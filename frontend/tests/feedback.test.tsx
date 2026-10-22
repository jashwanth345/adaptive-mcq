import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { FeedbackDetail, FeedbackHistory, FeedbackQueue, ReportForm } from '../src/feedback/Feedback';
import { ApiError } from '../src/api';
const call=vi.fn();const id='11111111-1111-4111-8111-111111111111';let user={roles:['student']};
vi.mock('../src/auth',()=>({useAuth:()=>({authenticated:call,user})}));
const base={version_id:id,version:1,stem:'Synthetic reported question',state:'open',revision:1,confirmed_defect:false,grade_review:'not_required',exposures:5,reporters:2,open_reporters:2,helpful:1,poor:0,completed_attempts:5,release_state:'approved',priority:'standard',report_ratio:.4};
const detail={summary:base,reports:[{id,category:'ambiguous',rating:null,comment:'Synthetic unclear wording',state:'open',created_at:'2026-10-13T10:00:00Z'}],total_reports:1,decisions:[]};
beforeEach(()=>{call.mockReset();user={roles:['student']};});
function mount(view: 'report'|'history'|'queue'|'detail'){return render(<MemoryRouter initialEntries={[`/feedback-review/${id}`]}><Routes><Route path="/feedback-review/:versionId" element={view==='report'?<ReportForm attemptId={id} versionId={id} number={1}/>:view==='history'?<FeedbackHistory/>:view==='queue'?<FeedbackQueue/>:<FeedbackDetail/>}/></Routes></MemoryRouter>);}

it('sends a rating with exact version and no client identity',async()=>{
 call.mockResolvedValue({duplicate:false});mount('report');await userEvent.click(screen.getByText('Report or rate question 1'));
 await userEvent.selectOptions(screen.getByLabelText('Feedback category for question 1'),'rating');await userEvent.selectOptions(screen.getByLabelText('Rating for question 1'),'poor');await userEvent.type(screen.getByLabelText('Feedback comment for question 1'),'Needs clearer wording');await userEvent.click(screen.getByRole('button',{name:'Send feedback'}));
 expect(await screen.findByText(/Feedback saved/)).toBeVisible();const body=call.mock.calls[0][1].body;expect(body).toMatchObject({version_id:id,category:'rating',rating:'poor',comment:'Needs clearer wording'});expect(body).not.toHaveProperty('student_id');
});
it('retains comments and reuses a retry key after a failed report',async()=>{
 call.mockRejectedValue(new ApiError(503,'DATABASE_UNAVAILABLE'));mount('report');await userEvent.click(screen.getByText('Report or rate question 1'));await userEvent.type(screen.getByLabelText('Feedback comment for question 1'),'An ambiguous sentence');await userEvent.click(screen.getByRole('button',{name:'Send feedback'}));await screen.findByRole('alert');await userEvent.click(screen.getByRole('button',{name:'Send feedback'}));await waitFor(()=>expect(call).toHaveBeenCalledTimes(2));expect(call.mock.calls[0][1].body.idempotency_key).toBe(call.mock.calls[1][1].body.idempotency_key);expect(screen.getByLabelText('Feedback comment for question 1')).toHaveValue('An ambiguous sentence');
});
it('explains deduplicated feedback without claiming a new report',async()=>{
 call.mockResolvedValue({duplicate:true});mount('report');await userEvent.click(screen.getByText('Report or rate question 1'));await userEvent.click(screen.getByRole('button',{name:'Send feedback'}));expect(await screen.findByText(/original report is preserved/)).toBeVisible();
});
it('shows honest empty history and blocks teacher history access',async()=>{
 call.mockResolvedValue({items:[],total:0});const page=mount('history');expect(await screen.findByText('No feedback yet')).toBeVisible();page.unmount();call.mockClear();user={roles:['teacher']};mount('history');expect(screen.getByText('Student access required')).toBeVisible();expect(call).not.toHaveBeenCalled();
});
it('shows denominators and configurable priority without claiming accuracy',async()=>{
 call.mockResolvedValue({items:[base],total:1,policy:{minimum_reporters:3,report_ratio:.2}});mount('queue');expect(await screen.findByText(/2 unresolved reporters \/ 5 exposed students/)).toBeVisible();expect(screen.getByText(/Counts are not an accuracy measure/)).toBeVisible();expect(screen.getByRole('link',{name:'Review reports'})).toHaveAttribute('href',`/feedback-review/${id}`);
});
it('requires explicit quarantine confirmation and sends the current revision',async()=>{
 user={roles:['teacher']};call.mockImplementation(async(_path,options)=>options?.body?{}:detail);mount('detail');await screen.findByText('Synthetic reported question');await userEvent.selectOptions(screen.getByLabelText('Review action'),'confirm_defect');await userEvent.type(screen.getByLabelText('Decision and follow-up note'),'Source contradicts the key');expect(screen.getByRole('button',{name:'Save review decision'})).toBeDisabled();await userEvent.click(screen.getByRole('checkbox'));await userEvent.click(screen.getByRole('button',{name:'Save review decision'}));expect(await screen.findByText(/Review decision saved/)).toBeVisible();expect(call).toHaveBeenCalledWith(`/feedback/reviews/${id}/decisions`,expect.objectContaining({body:expect.objectContaining({revision:1,action:'confirm_defect'})}));
});
it('allows score-review acknowledgement without pretending to regrade or restore',async()=>{
 call.mockImplementation(async(_path,options)=>options?.body?{}:{...detail,summary:{...base,confirmed_defect:true,grade_review:'pending',state:'resolved'}});mount('detail');await screen.findByText('Score review: pending');expect(screen.queryByLabelText('Review action')).not.toBeInTheDocument();expect(screen.getByText(/Acknowledgement does not regrade/)).toBeVisible();await userEvent.type(screen.getByLabelText('Decision and follow-up note'),'Reviewed impact; correction planned');await userEvent.click(screen.getByRole('button',{name:'Acknowledge score review'}));expect(await screen.findByText(/Review decision saved/)).toBeVisible();expect(call).toHaveBeenCalledWith(`/feedback/reviews/${id}/decisions`,expect.objectContaining({body:expect.objectContaining({action:'acknowledge_grades'})}));
});
it('keeps failed decisions visible with no success claim',async()=>{
 call.mockImplementation(async(_path,options)=>{if(options?.body)throw new ApiError(409,'FEEDBACK_STALE');return detail;});mount('detail');await screen.findByText('Synthetic reported question');await userEvent.type(screen.getByLabelText('Decision and follow-up note'),'Check source again');await userEvent.click(screen.getByRole('button',{name:'Save review decision'}));expect(await screen.findByRole('alert')).toHaveTextContent('New feedback');expect(screen.getByLabelText('Decision and follow-up note')).toHaveValue('Check source again');expect(screen.queryByText(/Review decision saved/)).not.toBeInTheDocument();
});

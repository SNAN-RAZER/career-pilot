import {test} from 'node:test';
import assert from 'node:assert/strict';
import {localResume,normalizeJob,applicationOutcome} from '../lib/career.ts';
test('does not count upstream filled fallback as a confirmed submission',()=>{
 assert.equal(applicationOutcome({status:'applied',detail:'Fallback after Easy Apply failed: Web agent (filled)'}),'PREPARED');
 assert.equal(applicationOutcome({status:'applied',detail:'Naukri Easy Apply'}),'APPLIED');
 assert.equal(applicationOutcome({status:'skipped',detail:'MFA needed'}),'NEEDS_REVIEW');
 assert.equal(applicationOutcome({status:'failed'}),'FAILED');
});
test('extracts only present skills and contact from local resume text',()=>{
 const result=localResume('Sample Candidate\nsample@example.test\nReact and TypeScript developer. Node.js and SQL.');
 assert.equal(result.name,'Sample Candidate');assert.equal(result.email,'sample@example.test');
 assert.deepEqual(result.skills,['React','TypeScript','SQL','Node.js']);
 assert.throws(()=>localResume(' \n'),/no readable text/);
});
test('normalizes incomplete upstream results without unsafe listing links',()=>{
 const job=normalizeJob({job_id:'123',title:'Engineer',company:'Example',match_score:170,eligibility_score:-1,url:'javascript:alert(1)',reasons:['Real reason',null],tailored_skills:['React',false]});
 assert.equal(job.match,100);assert.equal(job.eligibility,0);assert.equal(job.url,undefined);assert.deepEqual(job.reasons,['Real reason']);assert.deepEqual(job.tags,['React']);
});

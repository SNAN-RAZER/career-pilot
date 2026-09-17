export type Job = { id:string; company:string; title:string; location:string; salary:string; match:number; eligibility?:number; color:string; mark:string; tags:string[]; status?:string; recommendation?:string; reasons?:string[]; missing?:string[]; summary?:string; url?:string; ats?:number; message?:string };
export type Preferences = { roles:string; location:string; experience:number; minMatch:number; limit:number; autoApply:boolean };
export const defaultPreferences:Preferences={roles:"Frontend Engineer, Software Engineer",location:"",experience:2,minMatch:85,limit:5,autoApply:false};
export function normalizeJob(a:Record<string,unknown>):Job {
 const strings=(v:unknown)=>Array.isArray(v)?v.filter((x):x is string=>typeof x==="string"):[];
 const score=(v:unknown)=>Math.max(0,Math.min(100,Number(v)||0));
 return {id:String(a.job_id),company:String(a.company||"Company"),title:String(a.title||"Untitled role"),location:String(a.location||"Not specified"),salary:"Salary not listed",match:score(a.match_score??a.score),eligibility:score(a.eligibility_score),color:"#365cdd",mark:String(a.company||"C").slice(0,1),tags:strings(a.tailored_skills).slice(0,4),status:String(a.status||"PENDING"),recommendation:String(a.recommendation||"REVIEW"),reasons:strings(a.reasons),missing:strings(a.missing_requirements),summary:typeof a.tailored_summary==="string"?a.tailored_summary:undefined,url:typeof a.url==="string"&&/^https?:\/\//.test(a.url)?a.url:undefined,ats:typeof a.ats_score==="number"?a.ats_score:undefined,message:typeof a.apply_message==="string"?a.apply_message:undefined};
}
type ApiData = Record<string,unknown> & {connected:boolean;configured:boolean;message:string;detail:string;facts:Record<string,unknown>;tailored_summary:string;tailored_skills:string[];ats_score:number};
export async function careerApi(path:string,body?:unknown,method?:string):Promise<ApiData>{
 const form=body instanceof FormData;
 const response=await fetch(`/api/career/${path}`,{method:method||(body!==undefined?"POST":"GET"),headers:form?undefined:body!==undefined?{"Content-Type":"application/json"}:undefined,body:body===undefined?undefined:form?body:JSON.stringify(body)});
 const data=await response.json().catch(()=>({detail:"The agent returned an unreadable response."})) as ApiData;
 if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"This action could not be completed. Please check your connection.");
 return data;
}
export function localResume(text:string){
 if(!text.trim())throw new Error("This file has no readable text.");
 const known=["React","TypeScript","JavaScript","Python","Java","SQL","Node.js","Next.js","AWS","Docker","Kubernetes","Figma","CSS","HTML","Git","Go","C++","Excel","Product management","Data analysis","Machine learning"];
 const lower=text.toLowerCase();
 return {name:text.split(/\r?\n/).find(l=>l.trim())?.trim().slice(0,100)||"Your resume",email:text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0]||"",skills:known.filter(s=>new RegExp(`(^|[^a-z])${s.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}([^a-z]|$)`).test(lower)),source_text:text.slice(0,40000)};
}
export function applicationOutcome(result:Record<string,unknown>){
 const status=String(result.status||"").toLowerCase();const detail=String(result.detail||result.message||"");
 // Upstream auto-apply can say applied for a browser form that was merely filled.
 if(/filled|fill the form|prepared|submit in chrome/i.test(detail))return "PREPARED";
 if(status==="submitted"||status==="applied")return "APPLIED";
 if(status==="failed")return "FAILED";
 return "NEEDS_REVIEW";
}

import { env } from "cloudflare:workers";

const headers={"Cache-Control":"no-store"};
const json=(data:unknown,status=200)=>Response.json(data,{status,headers});
const allowedGet=/^(health|profile|llm\/settings|applications|applications\/[^/]+|applications\/[^/]+\/resume-file)$/;
const allowedPost=/^(profile\/(parse|store)|jobs\/search|applications\/[^/]+\/(tailor|auto-apply|web-apply|interview|offer|reject))$/;
async function handle(request:Request,context:{params:Promise<{path:string[]}>}){
 const {path}=await context.params;
 if(path.some(p=>!p||p==="."||p===".."||/[\\/\u0000]/.test(p)))return json({detail:"Invalid path."},400);
 const endpoint=path.join("/");
 const values=env as unknown as Record<string,string|undefined>;
 const base=values.CAREER_PILOT_API_URL;
 const token=values.CAREER_PILOT_API_TOKEN;
 if(endpoint==="status"&&request.method==="GET"){
  if(!base)return json({connected:false,configured:false,message:"Your agent is not connected yet."});
  try{const r=await fetch(`${base.replace(/\/$/,"")}/health`,{headers:token?{Authorization:`Bearer ${token}`}:{},signal:AbortSignal.timeout(8000),redirect:"error"});const d=await r.json() as {service?:string;status?:string};return json({configured:true,connected:r.ok&&d.service==="career-pilot"&&d.status==="ok",message:r.ok?"Agent connection checked.":"The agent could not be reached."});}catch{return json({configured:true,connected:false,message:"The agent is unavailable. Check that it is running."});}
 }
 if(!(request.method==="GET"?allowedGet:allowedPost).test(endpoint))return json({detail:"Action not supported."},404);
 if(request.method==="POST"){
  const origin=request.headers.get("Origin");
  if(!origin||origin!==new URL(request.url).origin)return json({detail:"This action must start in your Career Pilot workspace."},403);
 }
 if(!base)return json({detail:"Connect your Career Pilot agent before using live features."},503);
 if(Number(request.headers.get("content-length")||0)>11*1024*1024)return json({detail:"Files must be 10 MB or smaller."},413);
 try{
  const url=new URL(base);
  if(url.protocol!=="https:"&&!(url.protocol==="http:"&&["localhost","127.0.0.1","[::1]"].includes(url.hostname)))return json({detail:"The agent connection must use HTTPS."},503);
  let body:ArrayBuffer|undefined;
  if(request.method==="POST"){body=await request.arrayBuffer();if(body.byteLength>11*1024*1024)return json({detail:"Files must be 10 MB or smaller."},413);}
  const outgoing=new Headers();if(token)outgoing.set("Authorization",`Bearer ${token}`);if(request.headers.has("Content-Type"))outgoing.set("Content-Type",request.headers.get("Content-Type")!);
  const suffix=endpoint.endsWith("/web-apply")?"?submit=false":"";
  const response=await fetch(`${base.replace(/\/$/,"")}/${path.map(encodeURIComponent).join("/")}${suffix}`,{method:request.method,headers:outgoing,body,redirect:"error",signal:AbortSignal.timeout(180000)});
  const resultHeaders=new Headers(headers);for(const h of ["Content-Type","Content-Disposition"])if(response.headers.has(h))resultHeaders.set(h,response.headers.get(h)!);
  return new Response(response.body,{status:response.status,headers:resultHeaders});
 }catch{return json({detail:"The agent did not finish this request. Check the application status before retrying; a submission may still be running."},502);}
}
export const GET=handle;export const POST=handle;

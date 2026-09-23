"use client";
import { useEffect, useState } from 'react';
import { careerApi } from '@/lib/career';

type Provider = { id:string; label:string; kind:string; base_url:string; chat_model:string; embedding_model:string; api_key?:string };
export function ModelSettings(){
 const [providers,setProviders]=useState<Provider[]>([]);
 const [provider,setProvider]=useState<Provider|null>(null);
 const [models,setModels]=useState<string[]>([]);
 const [embeddings,setEmbeddings]=useState<string[]>([]);
 const [username,setUsername]=useState('');const [password,setPassword]=useState('');
 const [missing,setMissing]=useState<string[]>([]);const [account,setAccount]=useState(false);const [busy,setBusy]=useState('');
 const [message,setMessage]=useState('');const [error,setError]=useState('');
 async function action(label:string,fn:()=>Promise<void>){setBusy(label);setError('');setMessage('');try{await fn();}catch(e){setError((e as Error).message);}finally{setBusy('');}}
 async function load(){const data=await careerApi('llm/settings');setProviders(data.providers as Provider[]);setProvider({...data.active as Provider,api_key:''});const setup=await careerApi('setup/status');setAccount(!!setup.account_configured);setMissing((setup.missing_dependencies||[]) as string[]);}
 useEffect(()=>{void action('Loading settings…',load);},[]);
 async function save(){if(!provider)return;await careerApi('llm/providers',provider);await careerApi('llm/activate',{provider_id:provider.id,chat_model:provider.chat_model,embedding_model:provider.embedding_model});setProvider({...provider,api_key:''});setProviders(a=>a.map(p=>p.id===provider.id?{...provider,api_key:''}:p));setMessage('Model settings saved. Test the connection before uploading your resume.');}
 return <section className="settings-panel workflow-form" style={{gridColumn:'1 / -1'}}><h2>Models & job account</h2><p>Use either LM Studio or Ollama. Start its local server, load a chat model and an embedding model, then enter their exact IDs below.</p>{provider&&<>
 <label>Provider<select value={provider.id} disabled={!!busy} onChange={e=>{const p=providers.find(p=>p.id===e.target.value);if(p){setProvider({...p,api_key:''});setModels([]);setEmbeddings([]);}}}>{providers.filter(p=>p.kind!=='anthropic').map(p=><option key={p.id} value={p.id}>{p.label}</option>)}</select></label>
 <label>Server URL<input value={provider.base_url} onChange={e=>setProvider({...provider,base_url:e.target.value})} placeholder="http://127.0.0.1:1234/v1"/></label>
 <label>API key (if required)<input type="password" autoComplete="new-password" value={provider.api_key||''} onChange={e=>setProvider({...provider,api_key:e.target.value})} placeholder="Leave blank to keep your existing key"/></label>
 <button className="secondary" disabled={!!busy} onClick={()=>action('Loading available models…',async()=>{await careerApi('llm/providers',provider);const d=await careerApi(`llm/providers/${encodeURIComponent(provider.id)}/models`);if(!d.reachable)throw new Error("No models are available. Start your model server and load a model, then try again.");setModels(d.models as string[]);setEmbeddings(d.embedding_models as string[]);setMessage(`${d.count} chat models found. Choose your chat and embedding models.`);})}>Load available models</button>
 <div className="field-pair"><label>Chat model<input list="chat-models" value={provider.chat_model} onChange={e=>setProvider({...provider,chat_model:e.target.value})} placeholder="Exact model ID"/><datalist id="chat-models">{models.map(m=><option key={m} value={m}/>)}</datalist></label><label>Embedding model<input list="embedding-models" value={provider.embedding_model} onChange={e=>setProvider({...provider,embedding_model:e.target.value})} placeholder="Exact embedding model ID"/><datalist id="embedding-models">{embeddings.map(m=><option key={m} value={m}/>)}</datalist></label></div>
 <div className="button-row"><button className="primary" disabled={!!busy||!provider.chat_model||!provider.embedding_model} onClick={()=>action('Saving models…',save)}>Save models</button><button className="secondary" disabled={!!busy} onClick={()=>action('Testing chat and embeddings…',async()=>{await save();const d=await careerApi('setup/test-model',{});setMessage(d.message);})}>Save & test models</button></div></>}
 <hr/><h3>Naukri account</h3>{missing.length>0&&<p role="alert" className="form-error">Missing packages: {missing.join(", ")}. Double-click Start Career Pilot.cmd in the project folder to finish installation, then restart the server.</p>}<p>{account?'Credentials are saved on this PC. You can replace them below.':'Connect your account to search and apply to Naukri jobs.'} Credentials are stored in the local .env file, excluded from Git.</p>
 <label>Email<input type="email" autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)}/></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label>
 <div className="button-row"><button className="primary" disabled={!!busy||!username||!password} onClick={()=>action('Saving account…',async()=>{await careerApi('setup/account',{username,password});setPassword('');setAccount(true);setMessage('Account saved locally. Test login next.');})}>Save account</button><button className="secondary" disabled={!!busy||!account} onClick={()=>action('Testing login…',async()=>{const d=await careerApi('setup/test-account',{});setMessage(d.message);})}>Test login</button></div>
 {busy&&<p role="status">{busy}</p>}{message&&<p role="status" className="success-callout">{message}</p>}{error&&<p role="alert" className="form-error">{error}</p>}
 </section>;
}

#!/usr/bin/env python3
"""Refresh JXZNE historical AI subscription prices from a licensed public API.
Only successful source observations are stored; no inferred prices or country substitutions.
"""
import datetime as dt, json, os, pathlib, sys, time, urllib.request, urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'pricing-snapshots.json'
HISTORY=ROOT/'price-history'
API='https://subpriced.com/api/prices'
PRODUCTS=['chatgpt','claude','gemini','grok','perplexity','kimi','glm','deepseek','qwen','microsoft-copilot']
COUNTRIES={'US':'美国','TR':'土耳其','JP':'日本','GB':'英国','CA':'加拿大','FR':'法国','DE':'德国','IN':'印度','BR':'巴西','PH':'菲律宾','PK':'巴基斯坦','EG':'埃及','ID':'印度尼西亚','CN':'中国','NG':'尼日利亚','DK':'丹麦','AU':'澳大利亚','KR':'韩国','MX':'墨西哥','AR':'阿根廷','CH':'瑞士','TH':'泰国','VN':'越南','SG':'新加坡'}
NAMES={'chatgpt':'ChatGPT','claude':'Claude','gemini':'Gemini','grok':'Grok','glm':'GLM','leonardo-ai':'Leonardo AI','character-ai':'Character AI','perplexity':'Perplexity','microsoft-copilot':'Microsoft Copilot','manus':'Manus','kimi':'Kimi','poe':'Poe','sora':'Sora','kling-ai':'Kling AI','runwayml':'Runway','captions':'Captions','pollo-ai':'Pollo AI','heygen':'HeyGen','invideo-ai':'invideo AI','catcosplay':'CatCosplay','suno':'Suno','x':'X','le-chat':'Le Chat','deepseek':'DeepSeek','qwen':'Qwen'}
def pick(obj,*keys):
 for k in keys:
  if isinstance(obj,dict) and obj.get(k) is not None: return obj[k]
 return None
def records(x):
 if isinstance(x,list): return x
 if not isinstance(x,dict): return []
 for key in ('prices','data','results','items','rows','subscriptions','plans'):
  val=x.get(key)
  if isinstance(val,list): return val
  if isinstance(val,dict):
   nested=records(val)
   if nested:return nested
 return []
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'JXZNE-price-research/1.0 (public API; source attribution)','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=25) as r:return json.loads(r.read(5_000_000))
def normalized(record,id,now):
 if not isinstance(record,dict):return None
 # Never publish demo, placeholder or explicitly unverified prices.
 if record.get('is_demo') is True or record.get('demo') is True or record.get('is_placeholder') is True:return None
 if str(record.get('status','')).lower() in ('demo','placeholder','unverified','rejected'):return None
 item=record.get('price') if isinstance(record.get('price'),dict) else record
 country_obj=pick(item,'country_code','countryCode','region_code','region','country')
 if isinstance(country_obj,dict):country_obj=pick(country_obj,'code','iso2','country_code','id')
 country=str(country_obj or '').upper()
 if country not in COUNTRIES:return None
 plan_obj=pick(item,'plan','plan_name','tier','subscription','name')
 if isinstance(plan_obj,dict):plan_obj=pick(plan_obj,'name','title','slug')
 plan=str(plan_obj or '套餐未标记')[:90]
 channel_obj=pick(item,'platform','channel','store','source_type')
 if isinstance(channel_obj,dict):channel_obj=pick(channel_obj,'name','title','slug')
 channel=str(channel_obj or '未标记渠道')[:50]
 amount=pick(item,'price_usd','usd_price','usdPrice','usd','monthly_usd','amount_usd','usd_value','usdValue')
 try: usd=float(amount)
 except (ValueError,TypeError):return None
 if not 0 < usd < 5000:return None
 cycle=str(pick(item,'period','billing_period','interval','billingCycle') or 'monthly').lower()
 if cycle not in ('month','monthly','1 month','monthly subscription','per_month','month_1','1m'):
  # Never treat annual/weekly billing as monthly without verified conversion.
  return None
 source=str(pick(item,'source_url','sourceUrl','url','store_url') or '')
 if not source.startswith('https://'):return None
 date=str(pick(item,'last_verified','lastVerified','verified_at','observed_at','date','checked_at','last_updated','updatedAt') or '')[:10]
 try:dt.date.fromisoformat(date)
 except ValueError:return None
 original=pick(item,'local_price','price_local','amount_local','local_amount')
 currency=str(pick(item,'currency','currency_code','currencyCode') or '')
 result={'id':id,'product':NAMES[id],'plan':plan,'country':COUNTRIES[country],'code':country,'channel':channel,'usd':round(usd,4),'unit':'USD/月','date':date,'source':source,'fetchedAt':now,'dataset':'Subscription Price Monitor / OpenTheRank'}
 if original is not None and currency:
  result['localAmount']=str(original)[:32];result['currency']=currency[:8]
 return result
def main():
 now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
 today=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')
 old=json.loads(OUT.read_text('utf-8')) if OUT.exists() else {'rows':[]}
 collected={};worked=0;errors=[]
 for id in PRODUCTS:
  try:
   # Product endpoint may contain its entire country / plan catalog.
   # Fall back to paginated raw-price API; never use country/plan guesses.
   from urllib.parse import quote
   raw=[]
   try:
    raw=records(get('https://subpriced.com/api/services/'+quote(id)))
   except (urllib.error.URLError,TimeoutError,ValueError,json.JSONDecodeError) as e:
    print(id, 'service endpoint:', type(e).__name__)
   if not raw:
    for page in range(1,21):
     data=get(API+'?product='+quote(id)+'&page='+str(page))
     batch=records(data)
     if not batch:break
     raw.extend(batch)
     if len(batch)<20:break
     time.sleep(.6)
   valid=0
   for x in raw:
    row=normalized(x,id,now)
    if row:
     key=(row['id'],row['plan'],row['code'],row['channel'])
     prev=collected.get(key)
     if prev is None or row['date']>prev['date']:collected[key]=row
     valid+=1
   print(id,'raw records:',len(raw),'valid monthly observations:',valid)
   if valid:worked+=1
   else:errors.append(id+': no validated monthly rows')
  except (urllib.error.URLError,TimeoutError,ValueError,json.JSONDecodeError) as e:errors.append(id+': '+type(e).__name__)
  time.sleep(1.1)
 print('Validated products:',worked,'validated rows:',len(collected))
 print('Unavailable products:',', '.join(errors))
 if not collected:
  print('NO_NEW_VERIFIED_DATA: existing snapshot preserved; no new history created.')
  return 0
 def keep(x):
  if not isinstance(x,dict) or not all(k in x and x[k] not in ('',None) for k in ('id','plan','code','channel','source')):return False
  if not str(x.get('source','')).startswith('https://') or x.get('unit')!='USD/月':return False
  if str(x.get('status','')).lower() in ('demo','placeholder','unverified','rejected'):return False
  if x.get('is_demo') is True or x.get('demo') is True or x.get('is_placeholder') is True:return False
  try:
   usd=float(x.get('usd'));dt.date.fromisoformat(str(x.get('date') or '')[:10])
  except (TypeError,ValueError):return False
  return 0<usd<5000
 merged={(x['id'],x['plan'],x['code'],x['channel']):x for x in old.get('rows',[]) if keep(x)}
 for key,row in collected.items():
  prev=merged.get(key)
  if prev is None or row['date']>=prev.get('date',''):merged[key]=row
 rows=sorted(merged.values(),key=lambda x:(x['id'],x['plan'],x['code'],x['channel']))
 output={'about':'Observed, attributed, monthly subscription prices. USD equivalents are not API rates or guaranteed quotes.','lastReviewed':today,'lastSuccessfulFetch':now,'automatedRows':len(collected),'dataProvider':'Subscription Price Monitor / OpenTheRank, CC BY 4.0 (per provider statement)','dataProviderUrl':'https://subpriced.com/api-docs','rows':rows}
 HISTORY.mkdir(exist_ok=True)
 snapshot=HISTORY/(today+'.json')
 # Daily snapshot is immutable for a day; preserve earlier runs and only use one snapshot per day.
 if not snapshot.exists():snapshot.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n','utf-8')
 OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n','utf-8')
 print('Updated',len(rows),'rows; immutable history',snapshot)
 return 0
if __name__=='__main__':sys.exit(main())

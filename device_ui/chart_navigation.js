/* Browser history and viewport only; never changes acquisition or recording. */
const CHART_HISTORY_MS=180000,CHART_MAX_POINTS=60000;
class ChartNavigation {
  constructor(span=10000){this.span=span;this.end=0;this.follow=true;}
  range(oldest,latest){
    if(this.follow)this.end=latest;
    else this.end=Math.max(Math.min(latest,oldest+this.span),Math.min(latest,this.end));
    return {start:this.end-this.span,end:this.end,span:this.span};
  }
  zoom(factor,anchor,oldest,latest){
    const r=this.range(oldest,latest),at=r.start+r.span*anchor;
    this.span=Math.max(200,Math.min(CHART_HISTORY_MS,this.span*factor));
    this.end=at+this.span*(1-anchor);this.follow=false;return this.range(oldest,latest);
  }
  pan(delta,oldest,latest){this.range(oldest,latest);this.end+=delta;this.follow=false;return this.range(oldest,latest);}
  window(span,oldest,latest){this.span=span;return this.range(oldest,latest);}
  live(span=this.span){this.span=span;this.follow=true;}
}
function chartVisible(points,start,end){
  const bound=(time,upper)=>{let lo=0,hi=points.length;while(lo<hi){const m=(lo+hi)>>1;if(points[m].t<time||(upper&&points[m].t===time))lo=m+1;else hi=m;}return lo;};
  return points.slice(bound(start,false),bound(end,true));
}
function chartEnvelope(points,key,start,span,pixels){
  // Keep first/last/min/max per pixel, and explicit discontinuities. Peaks survive
  // reduction; invalid samples and configuration boundaries are never bridged.
  const result=[];let bucket=[],column=-1,previous=null;
  const flush=()=>{if(!bucket.length)return;let min=0,max=0;for(let i=1;i<bucket.length;i++){if(bucket[i][key]<bucket[min][key])min=i;if(bucket[i][key]>bucket[max][key])max=i;}
    for(const i of [...new Set([0,min,max,bucket.length-1])].sort((a,b)=>a-b))result.push(bucket[i]);bucket=[];};
  for(const p of points){
    const discontinuity=p.gap||(previous&&previous.revision!==p.revision);
    if(discontinuity){flush();result.push(null);}
    if(!Number.isFinite(p[key])){flush();result.push(null);previous=p;continue;}
    const next=Math.floor((p.t-start)/span*pixels);
    if(next!==column){flush();column=next;}
    bucket.push(p);previous=p;
  }
  flush();return result;
}
if(typeof module!=='undefined')module.exports={ChartNavigation,chartVisible,chartEnvelope,CHART_HISTORY_MS,CHART_MAX_POINTS};

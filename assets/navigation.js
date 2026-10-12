(function(){
var header=document.querySelector('body > header');
if(!header)return;
var last=Math.max(0,window.scrollY),distance=0,direction=0,scheduled=false;
function show(){header.classList.remove('header-hidden');}
function update(){
scheduled=false;
var y=Math.max(0,window.scrollY),delta=y-last;
last=y;
if(y<80||header.querySelector('[aria-expanded="true"]')){show();distance=0;return;}
var next=delta>0?1:delta<0?-1:direction;
if(next!==direction){distance=0;direction=next;}
distance+=delta;
if(distance>24){header.classList.add('header-hidden');distance=0;}
else if(distance<-10){show();distance=0;}
header.classList.toggle('header-scrolled',y>8);
}
window.addEventListener('scroll',function(){if(!scheduled){scheduled=true;requestAnimationFrame(update);}},{passive:true});
header.addEventListener('focusin',show);
header.addEventListener('click',show);
window.addEventListener('pageshow',function(){last=Math.max(0,window.scrollY);show();});
})();
/* Accessible photo navigation for individual collection photographs only. Trial version; revert this block if requested. */
(function(){
if(!document.body.classList.contains('photo-page'))return;
var nav=document.querySelector('.photo-nav');
if(!nav)return;
var next=nav.querySelector('[data-photo-direction="next"]');
var previous=nav.querySelector('[data-photo-direction="previous"], [data-photo-direction="prev"]');
var backToCollection=nav.querySelector('[data-photo-return]');
if(!next&&!previous)return;
var bar=document.createElement('nav');
bar.className='photo-quick-nav';
bar.setAttribute('aria-label','Quick photo navigation');
function add(link,label,cls){if(!link)return;var a=document.createElement('a');a.href=link.href;a.className=cls;a.textContent=label;a.setAttribute('aria-label',label==='Next →'?'Next photograph':label==='← Collection'?'Back to photo collection':'Previous photograph');bar.appendChild(a);}
if(previous){add(previous,'← Previous','photo-quick-prev');}else if(backToCollection){add(backToCollection,'← Collection','photo-quick-prev');}
add(next,'Next →','photo-quick-next');
document.body.appendChild(bar);
/* Hide duplicate in-page previous/next links; retain the collection return link. */
nav.querySelectorAll('[data-photo-direction]').forEach(function(link){link.style.display='none';});
var style=document.createElement('style');
style.textContent='.photo-page{padding-bottom:calc(76px + env(safe-area-inset-bottom,0px))}.photo-quick-nav{position:fixed;z-index:90;bottom:calc(14px + env(safe-area-inset-bottom,0px));left:50%;transform:translateX(-50%);display:flex;gap:10px;justify-content:center;align-items:center;padding:7px;background:rgba(250,247,240,.96);border:1px solid #cdbda9;border-radius:999px;box-shadow:0 6px 24px rgba(31,32,26,.2);backdrop-filter:blur(10px);max-width:calc(100vw - 32px)}.photo-quick-nav a{display:flex;align-items:center;justify-content:center;min-height:48px;min-width:110px;padding:0 18px;box-sizing:border-box;border-radius:999px;background:#354a34;color:#fff;text-decoration:none;font-weight:600;font-size:15px;white-space:nowrap}.photo-quick-nav a:hover{background:#253925}.photo-quick-nav a:focus-visible{outline:3px solid #a57b46;outline-offset:3px}@media(min-width:900px){.photo-quick-nav{bottom:24px}}';
document.head.appendChild(style);
})();

/* Seamless progression between Olympic National Park photo subcollections. */
(function(){
if(!document.body.classList.contains('photo-page'))return;
var name=location.pathname.split('/').pop();
var transitions={
'photo-42.html':{to:'photo-69.html',name:'Sol Duc Trail'},
'photo-50.html':{to:'photo-30.html',name:'Sol Duc Falls'},
'photo-32.html':{to:'photo-35.html',name:'Deer Lake'},
'photo-65.html':{to:'photo-75.html',name:'Hoh Rainforest'}
};
var starts={
'photo-69.html':{from:'photo-42.html',name:'Sol Duc Trail'},
'photo-30.html':{from:'photo-50.html',name:'Sol Duc Falls'},
'photo-35.html':{from:'photo-32.html',name:'Deer Lake'},
'photo-75.html':{from:'photo-65.html',name:'Hoh Rainforest'}
};
var bar=document.querySelector('.photo-quick-nav');
if(!bar)return;
var t=transitions[name];
if(t){
var next=bar.querySelector('.photo-quick-next');
if(next){next.href=t.to;next.textContent='Next collection →';next.setAttribute('aria-label','Continue to '+t.name+' photos');}
var note=document.createElement('p');note.className='photo-group-transition';note.textContent='Up next: '+t.name;bar.parentNode.insertBefore(note,bar);
}
var start=starts[name];
if(start){
var prev=bar.querySelector('.photo-quick-prev');if(prev){prev.href=start.from;prev.textContent='← Previous group';prev.setAttribute('aria-label','Previous photo group');}
var detail=document.querySelector('.photo-page .detail');
var h1=detail&&detail.querySelector('h1');
if(h1){var label=document.createElement('div');label.className='photo-new-group';label.innerHTML='<span>NEW PHOTO COLLECTION</span><strong></strong>';label.querySelector('strong').textContent=start.name;h1.parentNode.insertBefore(label,h1);}
}
var style=document.createElement('style');style.textContent='.photo-new-group{display:flex;align-items:center;flex-wrap:wrap;gap:8px 14px;margin:12px 0;padding:11px 14px;background:#e1e8d9;border-left:4px solid #526c49;border-radius:4px;color:#354a34}.photo-new-group span{font-size:11px;font-weight:700;letter-spacing:.12em}.photo-new-group strong{font:600 18px Georgia,serif}.photo-group-transition{position:fixed;bottom:calc(92px + env(safe-area-inset-bottom,0px));left:50%;transform:translateX(-50%);z-index:90;margin:0;padding:6px 12px;background:#f8f4ed;border:1px solid #cdbda9;border-radius:999px;font-size:12px;font-weight:600;color:#354a34;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.08)}.photo-quick-nav .photo-quick-next{min-width:0}@media(max-width:400px){.photo-quick-nav a{min-width:0;padding:0 13px;font-size:13px}}';document.head.appendChild(style);
})();

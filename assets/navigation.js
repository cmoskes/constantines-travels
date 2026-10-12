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
var previous=nav.querySelector('[data-photo-direction="prev"]');
if(!next&&!previous)return;
var bar=document.createElement('nav');
bar.className='photo-quick-nav';
bar.setAttribute('aria-label','Quick photo navigation');
function add(link,label,cls){if(!link)return;var a=document.createElement('a');a.href=link.href;a.className=cls;a.textContent=label;a.setAttribute('aria-label',label==='Next →'?'Next photograph':'Previous photograph');bar.appendChild(a);}
add(previous,'← Previous','photo-quick-prev');
add(next,'Next →','photo-quick-next');
document.body.appendChild(bar);
var style=document.createElement('style');
style.textContent='.photo-page{padding-bottom:calc(76px + env(safe-area-inset-bottom,0px))}.photo-quick-nav{position:fixed;z-index:90;bottom:calc(14px + env(safe-area-inset-bottom,0px));left:50%;transform:translateX(-50%);display:flex;gap:10px;justify-content:center;align-items:center;padding:7px;background:rgba(250,247,240,.96);border:1px solid #cdbda9;border-radius:999px;box-shadow:0 6px 24px rgba(31,32,26,.2);backdrop-filter:blur(10px);max-width:calc(100vw - 32px)}.photo-quick-nav a{display:flex;align-items:center;justify-content:center;min-height:48px;min-width:110px;padding:0 18px;box-sizing:border-box;border-radius:999px;background:#354a34;color:#fff;text-decoration:none;font-weight:600;font-size:15px;white-space:nowrap}.photo-quick-nav a:hover{background:#253925}.photo-quick-nav a:focus-visible{outline:3px solid #a57b46;outline-offset:3px}@media(min-width:900px){.photo-quick-nav{bottom:24px}}';
document.head.appendChild(style);
})();

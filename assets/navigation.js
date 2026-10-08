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
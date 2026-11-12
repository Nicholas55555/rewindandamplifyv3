(function(root){'use strict';
  function clamp(x,a,b){return Math.max(a,Math.min(b,x));}
  function ramseyProbability(detuningHz, interrogationSeconds, coherenceSeconds, contrast=1, readoutError=0.02, readoutErrorOne=0.04){
    if(![detuningHz,interrogationSeconds,coherenceSeconds,contrast,readoutError,readoutErrorOne].every(Number.isFinite)||interrogationSeconds<0||coherenceSeconds<=0||contrast<0||contrast>1||readoutError<0||readoutError>0.5||readoutErrorOne<0||readoutErrorOne>0.5) throw new RangeError('Invalid Ramsey settings');
    const p=0.5*(1+contrast*Math.exp(-interrogationSeconds/coherenceSeconds)*Math.sin(2*Math.PI*detuningHz*interrogationSeconds));
    return readoutError+(1-readoutError-readoutErrorOne)*p;
  }
  function amplifyProbability(p,r){if(!Number.isFinite(p)||p<0||p>1||!Number.isInteger(r)||r<0)throw new RangeError('Invalid amplification parameters');return Math.sin((2*r+1)*Math.asin(Math.sqrt(p)))**2;}
  const api={clamp,ramseyProbability,amplifyProbability};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.DiagnosticModel=api;
})(typeof globalThis!=='undefined'?globalThis:this);

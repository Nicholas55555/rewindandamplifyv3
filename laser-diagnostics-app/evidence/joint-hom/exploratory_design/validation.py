"""Fresh independent-block validation and stronger classical sequence controls."""
import itertools
import numpy as np
from inference import hmm_forward,hmm_score

MASTER=20261112047
BLOCKS=np.array(list(itertools.product(range(3),repeat=4)),dtype=np.uint8)
BUDGETS=[16,64,256,646,1024,1911]


def rng(*namespace):
    return np.random.default_rng(np.random.SeedSequence(MASTER,spawn_key=namespace))


def normalized(p):
    p=np.asarray(p,dtype=float)
    if not np.all(np.isfinite(p)) or p.min() < -1e-12 or abs(p.sum()-1)>1e-10:
        raise ValueError('Invalid finite-block probability law')
    p=np.maximum(p,0.);return p/p.sum()


def sample_blocks(p,n,namespace):
    return BLOCKS[rng(*namespace).choice(len(p),size=n,p=normalized(p))]


def block_indices(records):
    return records@np.array([27,9,3,1])


def fit_categorical(records):
    counts=np.bincount(block_indices(records),minlength=81)+.5
    return counts/counts.sum()


def fit_hmm(records,states,starts=10,max_iterations=200,tolerance=1e-7):
    """Local multi-start Baum-Welch; one setting/context, matched training data."""
    contexts=np.zeros(records.shape[1],dtype=int)
    candidates=[]
    for start in range(starts):
        generator=rng(6,states,start)
        initial=generator.dirichlet(np.ones(states))
        transition=generator.dirichlet(np.ones(states),size=states)
        emission=generator.dirichlet(np.ones(3),size=(1,states))
        history=[]
        for iteration in range(max_iterations):
            alpha,scales=hmm_forward(initial,transition,emission,records,contexts)
            history.append(float(np.log(scales).sum()))
            if iteration and abs(history[-1]-history[-2])/records.size<tolerance:break
            beta=np.ones_like(alpha)
            for t in range(records.shape[1]-2,-1,-1):
                next_emission=emission[0][:,records[:,t+1]].T
                beta[t]=(beta[t+1]*next_emission)@transition.T/scales[t+1,:,None]
            gamma=alpha*beta;gamma/=gamma.sum(axis=2,keepdims=True)
            initial=gamma[0].mean(axis=0)
            transition_counts=np.full((states,states),1e-8)
            for t in range(records.shape[1]-1):
                next_emission=emission[0][:,records[:,t+1]].T
                right=beta[t+1]*next_emission/scales[t+1,:,None]
                transition_counts+=transition*(alpha[t].T@right)
            transition=transition_counts/transition_counts.sum(axis=1,keepdims=True)
            counts=np.full((1,states,3),1e-8)
            for t in range(records.shape[1]):
                for outcome in range(3):counts[0,:,outcome]+=gamma[t,records[:,t]==outcome].sum(axis=0)
            emission=counts/counts.sum(axis=2,keepdims=True)
        model={'initial':initial,'transition':transition,'emission':emission}
        score=float(hmm_score(model,records,contexts).sum())
        candidates.append({'model':model,'start':start,'training_log_likelihood':score,
                           'iterations':len(history),'training_trace':history})
        print(f'HMM states={states}, start={start}, iterations={len(history)}, train={score:.6f}',flush=True)
    best=max(candidates,key=lambda x:x['training_log_likelihood'])
    report={k:v for k,v in best.items() if k!='model'}
    report.update({'states':states,'starts':starts,'maximum_iterations':max_iterations,'tolerance_nats_per_pair':tolerance,
                   'training_blocks':len(records),'parameters':(states-1)+states*(states-1)+2*states,
                   'all_start_final_scores':[c['training_log_likelihood'] for c in candidates],
                   'all_start_iterations':[c['iterations'] for c in candidates],
                   'model':{k:v.tolist() for k,v in best['model'].items()}})
    return best['model'],report


def namespaces(case_count=7):
    return [(1,i) for i in range(3)]+[(2,),(3,)]+[(4,j) for j in range(len(BUDGETS))]+[(5,j,k) for j in range(len(BUDGETS)) for k in range(case_count)]+[(6,s,i) for s in [4,8] for i in range(10)]

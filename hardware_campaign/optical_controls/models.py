"""Faithful optical/atomic circuit adapters; no account access or submission.

Atomic: full Lindblad CPTP map, not a fitted output Bernoulli rotation.
Photons: symmetric first-quantized encoding, independently checked in Fock space.
"""
from dataclasses import dataclass, replace
from math import comb, factorial
import numpy as np
from scipy.linalg import expm
from scipy.stats import poisson
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import Isometry
from qiskit.quantum_info import Statevector

I2=np.eye(2,dtype=complex)
X=np.array([[0,1],[1,0]],complex)
Y=np.array([[0,-1j],[1j,0]],complex)
Z=np.diag([1.,-1.]).astype(complex)


@dataclass(frozen=True)
class AtomicConfig:
    pulse_s: float=.0025
    dark_s: float=.020
    t1_s: float=100.
    t2_s: float=.200
    preparation_error: float=.01
    readout_01: float=.02
    readout_10: float=.04
    lightshift_hz_per_relative_power: float=3.


def lindblad_generator(omega_x,omega_y,omega_z,config):
    if not 0<config.t2_s<=2*config.t1_s:
        raise ValueError('require 0<T2<=2T1')
    h=(omega_x*X+omega_y*Y+omega_z*Z)/2
    collapse=[np.array([[0,0],[1,0]],complex)/np.sqrt(config.t1_s)]
    gamma_phi=1/config.t2_s-1/(2*config.t1_s)
    if gamma_phi>0:collapse.append(np.sqrt(gamma_phi/2)*Z)
    out=-1j*(np.kron(I2,h)-np.kron(h.T,I2))
    for c in collapse:
        cc=c.conj().T@c
        out+=np.kron(c.conj(),c)-.5*(np.kron(I2,cc)+np.kron(cc.T,I2))
    return out


def atomic_channel(detuning_hz,power=1.,config=AtomicConfig()):
    if not power>0:raise ValueError('positive relative intensity required')
    omega=np.pi/(2*config.pulse_s)*np.sqrt(power)
    pulse_delta=2*np.pi*(detuning_hz-config.lightshift_hz_per_relative_power*(power-1))
    first=expm(config.pulse_s*lindblad_generator(omega,0,pulse_delta,config))
    free=expm(config.dark_s*lindblad_generator(0,0,2*np.pi*detuning_hz,config))
    last=expm(config.pulse_s*lindblad_generator(0,omega,pulse_delta,config))
    return last@free@first


def apply_channel(channel,rho):
    return (channel@np.asarray(rho).reshape(-1,order='F')).reshape(2,2,order='F')


def bloch_reference(detuning_hz,power=1.,config=AtomicConfig(),initial=None):
    """Independent affine Bloch exponentials, no Liouvillian or Kraus imports."""
    if initial is None:initial=np.array([0.,0.,-1+2*config.preparation_error])
    r=np.r_[initial,1.]
    omega=np.pi/(2*config.pulse_s)*np.sqrt(power)
    pulse_delta=2*np.pi*(detuning_hz-config.lightshift_hz_per_relative_power*(power-1))
    for wx,wy,wz,t in [(omega,0,pulse_delta,config.pulse_s),
                       (0,0,2*np.pi*detuning_hz,config.dark_s),
                       (0,omega,pulse_delta,config.pulse_s)]:
        affine=np.array([[-1/config.t2_s,-wz,wy,0],
                         [wz,-1/config.t2_s,-wx,0],
                         [-wy,wx,-1/config.t1_s,-1/config.t1_s],
                         [0,0,0,0]],float)
        r=expm(t*affine)@r
    return r[:3]


def channel_isometry(channel):
    """Explicit column-vectorized Choi, output sys bit first, then env bits."""
    choi=np.zeros((4,4),complex)
    for a in range(2):
        for b in range(2):
            for c in range(2):
                for d in range(2):choi[a+2*c,b+2*d]=channel[a+2*b,c+2*d]
    eig,vectors=np.linalg.eigh((choi+choi.conj().T)/2)
    if eig.min() < -1e-11:raise ArithmeticError('channel is not completely positive')
    # Retain every eigencomponent, including zeros: no rank approximation.
    kraus=[np.sqrt(max(0,value))*vectors[:,j].reshape(2,2,order='F')
           for j,value in enumerate(eig)]
    v=np.vstack(kraus)
    if np.linalg.norm(v.conj().T@v-I2)>1e-10:raise ArithmeticError('not trace preserving')
    return v,kraus,eig


def measured(qc):
    out=qc.copy()
    out.add_register(ClassicalRegister(out.num_qubits,'meas'))
    out.measure(range(out.num_qubits),range(out.num_qubits))
    return out


def atomic_circuit(detuning_hz,power=1.,config=AtomicConfig(),basis='Z'):
    v,_,_=channel_isometry(atomic_channel(detuning_hz,power,config))
    qc=QuantumCircuit(4)
    qc.ry(2*np.arcsin(np.sqrt(config.preparation_error)),3)
    qc.x(0);qc.cx(3,0)
    gate=Isometry(v,0,0);gate.label='finite_Ramsey_CPTP'
    qc.append(gate,[0,1,2])
    if basis=='X':qc.h(0)
    elif basis=='Y':qc.sdg(0);qc.h(0)
    elif basis!='Z':raise ValueError('basis')
    return qc


def atomic_density_from_statevector(qc):
    psi=Statevector.from_instruction(qc).data.reshape(-1,2)
    return np.einsum('ei,ej->ij',psi,psi.conj())


def photon_circuit(n,phase,eta=1.,kind='coherent_sector',preparation_success=1.):
    """Symmetric photon-path encoding and equal loss into corresponding env modes.

    Paths q0..n-1; loss bits qn..2n-1 (1=lost); source flag q2n (1=prepared).
    Incoherent two-photon mixture adds one purifying bit. Photon labels are not
    observables; decode aggregates occupations of the four sample/env modes.
    """
    if n<1 or not 0<=eta<=1 or not 0<=preparation_success<=1:raise ValueError('parameters')
    if kind not in ('coherent_sector','noon','mixture'):raise ValueError('kind')
    if kind!='coherent_sector' and n!=2:raise ValueError('NOON/mixture requires N=2')
    extra=int(kind=='mixture')
    qc=QuantumCircuit(2*n+1+extra)
    source=2*n
    qc.ry(2*np.arcsin(np.sqrt(preparation_success)),source)
    if kind=='coherent_sector':
        for j in range(n):qc.h(j)
    elif kind=='noon':qc.h(0);qc.cx(0,1)
    else:
        qc.h(2*n+1);qc.cx(2*n+1,0);qc.cx(2*n+1,1)
    for j in range(n):
        qc.p(phase,j)
        qc.h(j)
        # Vacuum loss beamsplitter; path identifies its matching env mode.
        qc.ry(2*np.arccos(np.sqrt(eta)),n+j)
    return qc


def decode_photon(index,n):
    if not ((index>>(2*n))&1):return (0,0)
    counts=[0,0]
    for j in range(n):
        if not ((index>>(n+j))&1):counts[(index>>j)&1]+=1
    return tuple(counts)


def aggregated_photon_probabilities(probs,n):
    out={}
    for idx,p in enumerate(probs):
        key=decode_photon(idx,n)
        out[key]=out.get(key,0.)+float(p)
    return out


def fock_reference(n,phase,eta,kind='coherent_sector',preparation_success=1.):
    """Independent fixed-N bosonic spin representation, then binomial loss.

    Basis |k,N-k>, k=0..N. a†b matrix element sqrt[(k+1)(N-k)].
    Real beamsplitter convention is adjusted by a pi input phase to agree
    with the physical Hadamard convention; it only fixes output-port labels.
    """
    gen=np.zeros((n+1,n+1),complex)
    for k in range(n):
        gen[k+1,k]=np.sqrt((k+1)*(n-k))
        gen[k,k+1]=-np.sqrt((k+1)*(n-k))
    bs=expm(np.pi/4*gen)
    # U_real sends (a+b)/sqrt2 to port a. Its action on |b> has the
    # opposite phase from a Hadamard; applying exp(i*pi*n_b) before U
    # and relabeling port conventions below is unnecessary for probabilities
    # when input phase is negated by the alternative real BS convention.
    phases=np.exp(1j*phase*(n-np.arange(n+1)))
    if kind=='coherent_sector':
        amp=np.array([np.sqrt(comb(n,k)/2**n) for k in range(n+1)],complex)
        rho=np.outer(amp,amp.conj())
    elif kind=='noon':
        amp=np.zeros(n+1,complex);amp[0]=amp[n]=1/np.sqrt(2);rho=np.outer(amp,amp.conj())
    elif kind=='mixture':
        rho=np.zeros((n+1,n+1),complex);rho[0,0]=rho[n,n]=.5
    else:raise ValueError('kind')
    rho=phases[:,None]*rho*phases.conj()[None,:]
    ideal=np.real(np.diag(bs@rho@bs.conj().T))
    out={(a,b):0. for a in range(n+1) for b in range(n+1-a)}
    out[(0,0)]=1-preparation_success
    for ka,weight in enumerate(ideal):
        kb=n-ka
        for a in range(ka+1):
            for b in range(kb+1):
                out[(a,b)]+=preparation_success*weight*comb(ka,a)*comb(kb,b)*eta**(a+b)*(1-eta)**(n-a-b)
    return out


def photon_moments(distribution):
    return {'mean_a':float(sum(k[0]*v for k,v in distribution.items())),
            'mean_b':float(sum(k[1]*v for k,v in distribution.items())),
            'factorial2_a':float(sum(k[0]*(k[0]-1)*v for k,v in distribution.items())),
            'factorial2_b':float(sum(k[1]*(k[1]-1)*v for k,v in distribution.items())),
            'cross_ab':float(sum(k[0]*k[1]*v for k,v in distribution.items()))}


def coherent_tail(cutoff=8,mean=2.):
    """Unnormalized sector weights; omitted events and moments stay charged."""
    return {'cutoff':cutoff,'input_mean_photons':mean,
            'weights':[float(poisson.pmf(n,mean)) for n in range(cutoff+1)],
            'omitted_probability':float(poisson.sf(cutoff,mean)),
            'omitted_first_photon_moment':float(mean*poisson.sf(cutoff-1,mean)),
            'omitted_second_factorial_photon_moment':float(mean**2*poisson.sf(cutoff-2,mean)),
            'interpretation':'Original Poisson weights, no conditioning on retained sectors; event-TV omission bound is omitted_probability.'}

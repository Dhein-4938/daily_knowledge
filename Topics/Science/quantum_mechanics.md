---
title: Quantum Mechanics
date: '2026-03-14'
category: Science
subcategory: Physics
tags:
- superposition
- wave-function
- uncertainty-principle
status: current
confidence: high
read_time_minutes: 3
sources:
- type: wikipedia
  url: https://en.wikipedia.org/wiki/Quantum_mechanics
  retrieved: '2026-03-14'
  last_edited: '2026-03-12'
- type: arxiv
  id: 2603.12266v1
  title: 'MM-CondChain: A Programmatically Verified Benchmark for Visually Grounded
    Deep Compositional Reasoning'
  year: 2026
- type: arxiv
  id: 2603.12265v1
  title: 'OmniStream: Mastering Perception, Reconstruction and Action in Continuous
    Streams'
  year: 2026
- type: arxiv
  id: 2603.12263v1
  title: '$Ψ_0$: An Open Foundation Model Towards Universal Humanoid Loco-Manipulation'
  year: 2026
generated_by: claude-sonnet-4-6
reviewed: false
discussion_ready: true
---

# Quantum Mechanics

```markdown
---
title: Quantum Mechanics
tags: [physics, foundations, quantum]
date: 2026-03-14
---

## Core Concept

> [!info] Definition
> Quantum mechanics (QM) is the fundamental theory governing matter and radiation at atomic and subatomic scales. Its state space is a **complex Hilbert space** $\mathcal{H}$, and the state of a system is encoded in a normalized vector $|\psi\rangle \in \mathcal{H}$ — the *wave function*.

Time evolution is unitary and governed by the **Schrödinger equation**:

$$i\hbar \frac{\partial}{\partial t}|\psi(t)\rangle = \hat{H}|\psi(t)\rangle$$

where $\hat{H}$ is the Hamiltonian operator. Observable quantities correspond to self-adjoint operators $\hat{A}$; a measurement yields eigenvalue $a_n$ with probability $|\langle a_n | \psi \rangle|^2$ (Born rule), collapsing $|\psi\rangle$ to $|a_n\rangle$.

Classical mechanics emerges as an approximation in the limit $\hbar \to 0$ (or equivalently, when action $S \gg \hbar$), formalized via the [[WKB Approximation]] and [[Ehrenfest's Theorem]].

---

## Why It Matters

QM is not merely a theory of the small — it is the bedrock of:

- **Chemistry**: molecular bonding, spectroscopy, reaction rates ([[Quantum Chemistry]])
- **Materials science**: band theory, superconductivity, topological phases
- **Technology**: transistors, lasers, MRI, and increasingly [[Quantum Computing]]
- **Cosmology**: quantum fluctuations seeding large-scale structure

> [!tip] Non-obvious connection
> The success of QM in thermodynamics is as striking as in mechanics. Planck's 1900 quantization of oscillator energies ($E = n\hbar\omega$) resolved the ultraviolet catastrophe of [[Blackbody Radiation]] — the first crack in classical physics, born from statistical necessity rather than dynamical insight.

---

## Key Details

**1. Superposition & Interference**
States can be linearly combined: $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$. Interference between probability amplitudes — not probabilities themselves — is the source of distinctly quantum phenomena like the double-slit pattern.

**2. Heisenberg Uncertainty Principle**
For conjugate observables $\hat{x}$ and $\hat{p}$:

$$\sigma_x \sigma_p \geq \frac{\hbar}{2}$$

This is not a measurement disturbance artifact but a fundamental property of non-commuting operators ($[\hat{x}, \hat{p}] = i\hbar$). Robertson's inequality generalizes it: $\sigma_A \sigma_B \geq \frac{1}{2}|\langle[\hat{A},\hat{B}]\rangle|$.

**3. Entanglement**
A two-particle state that cannot be factored as $|\psi_A\rangle \otimes |\psi_B\rangle$ is *entangled*. Bell's theorem (1964) proves no local hidden-variable theory can reproduce QM's predictions — confirmed experimentally (Aspect 1982, loophole-free tests 2015). Entanglement is the core resource in [[Quantum Information Theory]].

**4. The Measurement Problem**
The formalism is silent on *when* and *why* the wave function "collapses." This is genuinely unresolved. Interpretations — Copenhagen, Many-Worlds ([[Everett Interpretation]]), Bohmian mechanics, QBism — agree on predictions but differ radically on ontology.

**5. Path Integral Formulation**
Feynman's alternative: the amplitude for a transition is a sum over *all* paths weighted by $e^{iS/\hbar}$, where $S$ is the classical action. Equivalent to operator QM but geometrically illuminating and essential for [[Quantum Field Theory]].

---

## Current State

> [!warning] Note: this information may be dated

Active research frontiers include:

- **Quantum error correction & fault tolerance**: stabilizer codes, surface codes — prerequisite for scalable quantum computation
- **Quantum gravity**: reconciling QM with general relativity remains open; candidate frameworks include [[Loop Quantum Gravity]] and string theory
- **Many-body quantum systems**: tensor network methods (DMRG, MERA) for simulating strongly correlated matter
- **Quantum thermodynamics**: formalizing work, heat, and entropy at quantum scales, where thermal and quantum fluctuations compete
- **Foundations**: decoherence theory has largely displaced naïve Copenhagen collapse, but the measurement problem and the ontological status of $|\psi\rangle$ remain contested

---

## See Also

- [[Wave-Particle Duality]]
- [[Quantum Field Theory]]
- [[Quantum Computing]]
- [[Bell's Theorem and Nonlocality]]
- [[Density Matrix and Open Quantum Systems]]
- [[Path Integral Formulation]]

---

## Discussion Prompts

1. **Classicality from quantum**: Decoherence explains the *appearance* of collapse via entanglement with the environment — but does it genuinely solve the measurement problem, or merely relocate it? What would a satisfying solution require?

2. **Entanglement vs. information**: Bell violations rule out local realism, but quantum correlations cannot transmit information superluminally. Is nonlocality a feature of reality or an artifact of how we decompose composite systems?

3. **Discreteness as fundamental**: QM quantizes energy levels, angular momentum, and charge. Is discreteness a deep ontological fact, or does it emerge from an underlying continuous structure (e.g., continuous field configurations in QFT)?
```



---
*Wikipedia source: [Quantum Mechanics](https://en.wikipedia.org/wiki/Quantum_mechanics) · Retrieved 2026-03-14*

**Recent arXiv papers:**
- [MM-CondChain: A Programmatically Verified Benchmark for Visually Grounded Deep Compositional Reasoning](https://arxiv.org/abs/2603.12266v1) (2026)
- [OmniStream: Mastering Perception, Reconstruction and Action in Continuous Streams](https://arxiv.org/abs/2603.12265v1) (2026)
- [$Ψ_0$: An Open Foundation Model Towards Universal Humanoid Loco-Manipulation](https://arxiv.org/abs/2603.12263v1) (2026)
# Aerodynamic Analysis with Athena Vortex Lattice (AVL)

**Project**

Hochschule für Angewandte Wissenschaften Hamburg
*Hamburg University of Applied Sciences*

Department of Automotive and Aeronautical Engineering

**Author:** Kinga Budziak

**Supervisor:** Prof. Dr.-Ing. Dieter Scholz, MSME

**Delivery date:** 20.09.2015

---

## Abstract

This project evaluates the suitability and practicality of the program Athena Vortex Lattice (AVL) by Mark Drela. A short user guide was written to make it easier (especially for students) to get started with the program AVL. AVL was applied to calculate the induced drag and the Oswald factor. In a first task, AVL was used to calculate simple wings of different aspect ratio $A$ and taper ratio $\lambda$. The Oswald factor was calculated as a function $f(\lambda)$ in the same way as shown by Hoerner. Compared to Hoerner's function, the error never exceed 7.5 %. Surprisingly, the function $f(\lambda)$ was not independent of aspect ratio, as could be assumed from Hoerner. Variations of $f(\lambda)$ with aspect ratio were studied and general results found. In a second task, the box wing was investigated. Box wings of different $h/b$ ratio: 0.31; 0.62 and 0.93 were calculated in AVL. The induced drag and Oswald factor in all these cases was calculated. An equation, generally used in the literature, describes the box wing's Oswald factor with parameters $k_1$, $k_2$, $k_3$ and $k_4$. These parameters were found from results obtained with AVL by means of the Excel Solver. In this way the curve $k = f(h/b)$ was plotted. The curve was compared with curves with various theories and experiments conducted prior by other students. The curve built based on AVL fits very well with the curve from Hoerner, Prandtl and a second experiment made in the wind tunnel at HAW Hamburg.

---

*This work is protected by copyright.*
*The work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License: CC BY-NC-SA*

Any further request may be directed to:
Prof. Dr.-Ing. Dieter Scholz, MSME

---

## Task

**Aerodynamic Analysis with Athena Vortex Lattice (AVL)**

Task for a Project at HAW Hamburg

### Background

The Vortex Lattice Method (VLM) provides a quick understanding when induced drag is studied as a function of wing geometrical parameters. Previous studies in the research group AERO at HAW Hamburg used iDrag by Joel Grasmeyer and Tornado by Tomas Melin. The ideas was to get also familiar with AVL and to comment on it. For this software test, some beneficial investigation had to be set up. Geometries had to be found that would look worthwhile for a little investigation. Two ideas were selected. 1.) The (theoretical) Oswald factor of a wing described only by its aspect ratio $A$ and taper ratio $\lambda$ should be calculated and compared with Hoerner's results. Hoerner's curve was regarded as fundamental and some check was on the agenda. 2.) The (theoretical) Oswald factor (related to Oswald factor of its reference wing) should be calculated for a box wing. The geometrical parameters of interest were the $h/b$-ratio and the decalage. This was seen as useful, because wind tunnel measurements where obtained previously that needed further evaluation and background understanding.

### Task

Task is the evaluation of the AVL software by means of two example calculations. This includes the following subtasks:

- short literature review of the Vortex Lattice Method,
- description of AVL,
- comparison of the Oswald factor calculated with AVL for a simple wing described by its aspect ratio $A$ and taper ratio $\lambda$ with results from Hoerner,
- short literature review of box wing configurations,
- comparison of the Oswald factor (related to the Oswald factor of its reference wing) -- as a function of $h/b$-ratio and decalage -- with wind tunnel measurements.

The report has to be written based on German or international standards on report writing.

---

## Contents

- [List of Figures](#list-of-figures)
- [List of Tables](#list-of-tables)
- [List of Symbols](#list-of-symbols)
- [List of Abbreviations](#list-of-abbreviations)
- [1 Introduction](#1-introduction)
  - [1.1 Motivation](#11-motivation)
  - [1.2 Objectives](#12-objectives)
  - [1.3 Review of Literature](#13-review-of-literature)
  - [1.4 Structure of the Project](#14-structure-of-the-project)
- [2 AVL](#2-avl)
  - [2.1 Introduction](#21-introduction)
  - [2.2 Theoretical Background](#22-theoretical-background)
  - [2.3 User Guide](#23-user-guide)
- [3 Oswald Factor](#3-oswald-factor)
  - [3.1 Introduction](#31-introduction)
  - [3.2 Theoretical Background](#32-theoretical-background)
  - [3.3 AVL - Input Method](#33-avl---input-method)
  - [3.4 AVL -- Output Analysis](#34-avl--output-analysis)
- [4 Box Wing](#4-box-wing)
  - [4.1 Introduction](#41-introduction)
  - [4.2 Theoretical Background](#42-theoretical-background)
  - [4.3 AVL -- Input Geometry of the Box Wing](#43-avl--input-geometry-of-the-box-wing)
  - [4.4 AVL -- Output Analysis](#44-avl--output-analysis)
- [5 Summary](#5-summary)
- [References](#references)
- [Acknowledgements](#acknowledgements)

---

## List of Symbols

| Symbol | Description |
|--------|-------------|
| $A$ | Wing aspect ratio |
| $A_M$ | Aerodynamic influence matrix |
| $b$ | Wing span length |
| $b_N$ | Boundary condition |
| $b_w$ | Span of the wake behind the wing |
| $B_{ref}$ | Wing span used as a reference in AVL |
| $c$ | Wing chord length |
| $c_{BW}$ | Box wing chord |
| $c_{BW,ref}$ | Reference wing chord (for box wing) |
| $c_r$ | Wing root chord |
| $c_t$ | Wing tip chord |
| $C_{D,ff}$ | Induced drag coefficient calculated by AVL in Trefftz Plane |
| $C_{D,i}$ | Induced drag coefficient also called: drag due to the lift |
| $C_{D,0}$ | Zero-lift drag coefficient |
| $C_L$ | Lift coefficient |
| $C_L/\alpha$ | Lift curve slope |
| $C_{L,ff}$ | Lift coefficient calculated by AVL in Trefftz Plane |
| $C_m$ | Pitching moment coefficient |
| $D$ | Drag |
| $D_i$ | Induced drag |
| $D_{i,BW}$ | Box wing induced drag |
| $D_{i,BW,ref}$ | Reference wing induced drag (for box wing) |
| $dl$ | Infinitely small part of the filament |
| $dS$ | Infinitely small area of the wing |
| $d(y)$ | Drag distribution along span |
| $e$ | Oswald (efficiency) factor also called: span efficiency factor |
| $e_A$ | Average Oswald factor (among different $\alpha$) |
| $e_{BW}$ | Box wing Oswald factor |
| $e_{BW,ref}$ | Reference wing Oswald factor (for box wing) |
| $e_{theo}$ | Theoretical Oswald factor, inviscid drag due to lift only |
| $g$ | Gravitational acceleration |
| $h$ | Vertical stagger, vertical distance between horizontal wings of a box wing |
| $h/b$ | Vertical distance between horizontal wings of a box wing over a span |
| $k$ | Induced drag factor |
| $k_{e,F}$ | Correction factor: losses due to the fuselage |
| $k_{e,D0}$ | Correction factor: viscous drag due to the lift |
| $k_{e,M}$ | Correction factor: compressibility effects on induced drag |
| $L$ | Lift |
| $m$ | Wing mass |
| $n$ | Vector normal to the surface |
| $q$ | Dynamic pressure |
| $Q$ | Wing weight |
| $r$ | Radius from point P to the point on the filament |
| $R^2$ | Coefficient of determination from Excel |
| $S$ | Wing area |
| $S_{BW,ref}$ | Reference wing area (for box wing) |
| $S_{ref}$ | Wing area used as a reference in AVL |
| $u$ | Induced velocity, its component in x direction |
| $w$ | Induced velocity, its component in z direction |
| $v$ | Induced velocity, its component in y direction |
| $V$ | Velocity |
| $V_\infty$ | Air speed also called: freestream velocity |
| $V_{ind}$ | Induced velocity |
| $X$ | Axis of the coordinate system, downstream direction |
| $Y$ | Axis of the coordinate system, out the right wing direction |
| $Z$ | Axis of the coordinate system, up direction |

### Greek Symbols

| Symbol | Description |
|--------|-------------|
| $\alpha$ | Geometric angle of attack |
| $\alpha_0$ | Angle of attack corresponding to zero lift force |
| $\alpha_{eff}$ | Effective angle of attack |
| $\alpha_i$ | Induced angle of attack |
| $\beta$ | Sideslip angle |
| $\Gamma$ | Circulation |
| $\lambda$ | Wing taper ratio |
| $\lambda_{opt}$ | Optimum wing taper ratio according to Hoerner |
| $\rho$ | Air density |

### List of Subscripts

| Subscript | Description |
|-----------|-------------|
| $BW$ | Box wing configuration |
| $ff$ | Calculated in Trefftz Plane |
| $i=1,2,..$ | Arbitrary element from a group of elements |
| $r$ | Wing root |
| $ref$ | Reference dimension used in AVL |
| $BW,ref$ | Reference dimension used to comparison of a box wing and a rectangular wing |
| $t$ | Wing tip |
| $theo$ | Theoretical dimension obtained from formulas based on a particular model |

---

## List of Abbreviations

| Abbreviation | Description |
|--------------|-------------|
| AVL | Athena Vortex Lattice, program by Mark Drela and Harold Youngren for the aerodynamic and flight-dynamic analysis of rigid aircraft |
| Excel | Microsoft Excel, a spreadsheet application from Microsoft, used for calculation, graphs, macro programming |
| iDRAG | Program by Joel Grasmeyer to calculate induced drag |
| Tornado | Program by Tomas Melin for Linear Aerodynamic Wing Applications |
| Xfoil | Program by Mark Drela and Harold Youngren for the design and analysis of subsonic isolated airfoils |
| VLM | Vortex Lattice Method |

---

## 1 Introduction

### 1.1 Motivation

Nowadays, engineers have access to a wide variety of programs, which could be used to define aircraft geometry. The tool must be adequate to the task and user's knowledge. Different accuracy is needed for preliminary sizing of the plane model and different for the specific calculations of the passenger aircraft. The choice is between advanced programs -- based on expanded equations and consequently time-consuming, simple ones -- adequate only for limited number of cases or using rough numbers -- commonly accepted approximate values. Although advanced programs provide us with the results of better quality, it takes a lot of time to learn and then to use them. That is why it may be beneficial to get familiar with less complex program, which still offers reliable results. One of them will be evaluated in this project. This is AVL.

### 1.2 Objectives

The aim of this project is to learn how to operate AVL program, describe user's experience, decide if program is approachable and reliable. At the beginning, Oswald factors obtained by AVL and by theoretical formulas should be compared. In particular wings of different aspect ratio and different taper ratio should be examined. Afterwards, to verify results, a function $f(\lambda)$ should be created and compared with the one brought by Hoerner.

If the program seems to be reasonable, a student should have a look into box wing configuration and calculate Oswald factors for different $h/b$ ratio. Some students have already made analysis with iDrag, Tornado and research in the wind tunnel. Now similar analysis in AVL should be performed.

### 1.3 Review of Literature

There are two important sources that were of great help to me during learning about aerodynamic complexities and writing this project.

My favourite textbook is "Fundamentals of Aerodynamics" **Anderson 2001**. This book gives a good overview of aerodynamics and at the same time is understandable for students. It contains lots of informative illustrations and properly explained examples. Besides, it is up-to-date in comparison to many other aerodynamic books.

On the website of Stanford University, I found course notes from "*Applied Aerodynamics II*" **Kroo 2007.** They contain useful additional information, presented in a short and still very explanatory way.

### 1.4 Structure of the Project

The project is divided into five chapters

- **Chapter 2** gives theoretical background on Vortex Lattice Method and induced drag. Explains the way to use AVL.

- **Chapter 3** gives theoretical background on Oswald factor, includes analysis of Oswald factor and induced drag of wings with different aspect and taper ratio. Analysis is done in AVL and by means of Hoerner equation.

- **Chapter 4** gives theoretical background on box wing configuration, shows and comments results obtained from AVL: Oswald factor and induced drag. A new curve $k$ is compared with the ones from previous projects.

- **Chapter 5** is a summary of this project.

---

## 2 AVL

### 2.1 Introduction

AVL is an abbreviation of Athena Vortex Lattice. AVL was created by Mark Drela from MIT Aero & Astro and Harold Youngren. Information included in Chapter 2 comes substantially from this website (Drela and Youngren, 2010, 2013). As a description of the product it is written:

> *"AVL is a program for the aerodynamic and flight-dynamic analysis of rigid aircraft of arbitrary configuration. It employs an extended vortex lattice model for the lifting surfaces, together with a slender-body model for fuselages and nacelles. General nonlinear flight states can be specified. The flight dynamic analysis combines a full linearization of the aerodynamic model about any flight state, together with specified mass properties." (Drela and Youngren, 2013)*

It means that AVL is recommended to develop aircraft configuration. We can perform aerodynamic analysis and calculate such values as Oswald factor, angle of attack, lift, induced drag coefficients obtained in a Trefftz Plane. Besides we can perform dynamic stability analysis to calculate aerodynamic forces and moments and their derivatives. AVL is able to draw geometry of the wing or the fuselage and also plot results in Trefftz Plane, e.g. lift coefficient distribution along span. Other similar programs are iDrag by Joel Grasmeyer and Tornado by Tomas Melin.

### 2.2 Theoretical Background

#### 2.2.1 Vortex Lattice Theory

AVL is based on VLM method which stands for Vortex Lattice Method. It is a numerical method. VLM calculates lift curve slope, induced drag and lift distribution for the given wing configuration. In this method the wing is modeled with horseshoe vortices distributed along span and chord. Effects of thickness and viscosity are neglected. Horseshoe vortices are elements that produce lift. There are four important theories used to describe this effect and model the air flow around the wing.

a) Biot-Savart Law -- according to it, each vortex line of certain *circulation* induces velocity field. In an arbitrary point P, placed in a distance of radius $r$ from filament, the velocity induced by vortex is:

$$V = \frac{\Gamma}{4\pi} \int \frac{dl \times r}{|r|^3} \tag{2.1}$$

$dl$ -- infinitely small part of the filament
$r$ -- radius from point P to the point on the filament
$V$ -- induced velocity
$\Gamma$ -- strength of the vortex called circulation

**Figure 2.1** Vortex filament and illustration of the Biot-Savart law (Anderson, 2001).

b) Kutta-Joukovsky theorem -- according to it, a vortex of certain circulation moving with velocity $V$ experiences force. In the case regarding this paper it is a *bound vortex* fixed within the flow of velocity $V_\infty$ that produces lift:

$$L = \rho V_\infty \Gamma \tag{2.2}$$

$L$ -- lift
$V_\infty$ -- freestream velocity
$\rho$ -- air density

c) Hermann von Helmholtz theory -- which describes principles of vortex filament behaviour:
It must form a closed path -- e.g. vortex ring.
Circulation along one vortex filament is constant.

d) Prandtl lifting-line theory -- this is where the idea of *horseshoe vortex* comes from.

The horseshoe vortex is a simplified vortex ring. Vortex ring can be imitated by four vortex filaments, because vortex must always be closed. Figure 2.2 shows that it consists of a segment BC with a *bound vortex*, lines BA and CD starting in infinity with *trailing vortices* and a segment AD with a *starting vortex* (sometimes also called *free*). Since the starting vortex is placed in infinity, its influence can be neglected. Finally, there are just three filaments -- a horseshoe vortex (Liu, 2007).

**Figure 2.2** A detailed spanwise horseshoe vortex element (Katz and Plotkin, 1991).

$b$ -- wing span length
$c$ -- wing chord length

Another boundary conditions are:

Wake is modeled with trailing vortices, which go in local chord direction, parallel to $x$ direction. It is required for exact lift distribution, but it is not a real behaviour of a wake. In reality, they go in a freestream direction. Besides, no roll up effect is included (Gohl, 2009).

While calculating circulation of vortices, velocity on normal direction to the skeleton line is equal zero -- flow through the profile is impossible (2.3). It means that the sum of velocity of the freestream and the one due to the panel vortex on normal direction must be zero.

$$v \cdot n = 0 \tag{2.3}$$

**Figure 2.3** Influence of the cambering and the boundary condition: no flow through skeleton line (Melin, 2000).

This condition is calculated in collocation point placed in 3/4 of chord of the panel. A vortex of circulation $\Gamma$ is placed in 1/4 of the chord of the panel and it is an element that produces lift.

**Figure 2.4** Vortex lattice system on a finite wing (Anderson, 2001).

A surface of a wing is divided into panels in both direction: spanwise and chordwise. On each of the panels there is a horseshoe vortex. A sample sketch is shown in Figure 2.4. There are as many horseshoe vortices as there are panels, each of its own constant circulation. To get the whole aerodynamic force, contribution from all the panels must be summarized.

#### 2.2.2 Induced Drag

Induced drag coefficient is described with the symbol $C_{D,i}$. The other name is *drag due to the lift*, since it appears as a consequence of the lift. The difference in pressure on the wing: high on lower and low on upper surface, causes vortices at the tips of the wing.

**Figure 2.5** Three-dimensional flow over a finite wing. Flow curl around tips as a consequence of pressure imbalance (Anderson, 2001).

$c_t$ -- tip chord
$c_r$ -- root chord
$S$ -- wing area

Downstream close to the wing, these vortices drag the air around with them and as a consequence, it also induces velocity vector -- $V_{ind}$ at the wing. This vector is perpendicular to the freestream and in a negative direction. This effect influences other parts of the wing. It spreads along the whole span, slowly disappearing towards the root of the wing. It is called -- *downwash*. The effect is illustrated in Figure 2.6.
$w$ -- stands for velocity induced in z direction.

**Figure 2.6** Wing tip vortices visualisation (Lavionnaire, 2015).

Figure 2.7 presents downwash experienced by the wing modeled by one horseshoe vortex. If the wing is modeled not by one, but by many horseshoe vortices, an induced velocity at any control point comes from all the panels.

**Figure 2.7** Downwash distribution along the $y$ axis for a single horseshoe vortex (Anderson, 2001).

Downwash reduces lift, because $w$ -- changes the angle of attack seen by the profile. A new element, called *induced angle of attack* -- $\alpha_i$, is described by Equation (2.4) and presented in Figure 2.8.

$$\alpha_i = \arctan\left(\frac{w}{V_\infty}\right) \tag{2.4}$$

**Figure 2.8** Effect of downwash on the local flow over a local airfoil section of a finite wing (Anderson, 2001).

Now, the new angle of attack must be calculated (2.5). It is called *an effective angle of attack* -- $\alpha_{eff}$ and is presented in Figure 2.8.

$$\alpha_{eff} = \alpha - \alpha_i \tag{2.5}$$

$\alpha$ -- geometric (initial) angle of attack

For small angles of attack, lift coefficient will be calculated by Equation 2.6. $C_L$ is a function of $y$. It means it can vary along the wing span.

$$c_L(y_0) = \frac{c_L}{\alpha} \left[ \alpha_{eff}(y_0) - \alpha_0(y_0) \right] \tag{2.6}$$

$\alpha_0$ -- angle of attack corresponding to zero lift force
$C_L$ -- lift coefficient
$C_L/\alpha$ -- lift curve slope

By definition, the component of an aerodynamic force perpendicular to the freestream velocity vector is called *lift* and the one parallel to the freestream direction is called *drag*. Drag created as a consequence of the change from the initial $\alpha$ to $\alpha_{eff}$ is named *induced drag* -- $D_i$.

Usually induced drag is defined by Equation 2.7.

$$D_i = \frac{L^2}{q \pi b^2 e} \tag{2.7}$$

$e$ -- Oswald factor
$q$ -- dynamic pressure

According to Munk's stagger theorem (Munk, 1923), the calculations for induced drag can also be accomplished in the *Trefftz Plane*, plane infinitely far behind the wing (Figure 2.9), so called *far field analysis*. It is done by applying the momentum equation and the incompressible Bernoulli equation (Kroo, 2007a).

**Figure 2.9** Trefftz Plane used for calculation of induced drag (Katz and Plotkin, 1991).

$u$, $v$, and $w$ are the perturbation velocities in respectively $x$, $y$ and $z$ directions. The wake extends to infinity in the freestream direction. The drag depends only on the (perturbation) velocities induced in the Trefftz Plane. There, influence of $u$ can be neglected and drag can be defined by integrating $v$ and $w$ on the Trefftz Plane (2.8) (Kroo, 2007b).

$$D_i = \iint_{Trefftz\;Plane} v^2 + w^2 \, dS \tag{2.8}$$

$dS$ -- infinitely small area of the wing

After some transformations, $D_i$ can be calculated from Equation (2.9) (Katz and Plotkin, 1991).

$$D_i = -\frac{\rho}{2} \int_{-b_w/2}^{b_w/2} \Gamma(y) w \, dy \tag{2.9}$$

$b_w$ -- a span of the wake

Lift can be defined with Equation (2.10) (Kroo, 2007b) and calculated from (2.11) (Katz and Plotkin, 1991).

$$L = V_\infty \rho \iint_{\substack{top\;and\\bottom}} u \, dS - \rho \iint_{Trefftz\;Plane} uw \, dS \tag{2.10}$$

$$L = \rho V_\infty \int_{-b_w/2}^{b_w/2} \Gamma(y) \, dy \tag{2.11}$$

Due to the Trefftz Plane, calculations done with numerical methods are simplified. This is how AVL works as well.

#### 2.2.3 Wing Model in AVL -- Constraints

AVL creates system of equations to calculate distribution of the circulation. Equation (2.12) is such a basic equation system (Baier et al., 2013).

$$A_M \cdot \Gamma = b_N \tag{2.12}$$

$A_M$ -- aerodynamic influence matrix
$\Gamma$ -- circulation of each panel
$b_N$ -- boundary conditions

In AVL, wings are created as lifting surfaces, a fuselage as slender body. Aerodynamic model, which was described in previous subchapters, determines what can be analysed in AVL. These constraints are gathered in Table 2.1.

**Table 2.1** Possibilities and constraints of analysing the wing in AVL due to its aerodynamic model.

| CONSTRAINTS | CONSEQUENCES |
|-------------|--------------|
| Flow is potential (linear aerodynamic): incompressible, inviscid. | AVL does not give information when transition or stall effect happen. Reliable only for low Mach numbers. Only induced component of drag can be calculated. |
| No flow can get through the skeleton. | Cambered profile can be modeled, but of no thickness. |
| Trailing vortices going in chord direction. | The freestream must be at a reasonably small angle to the $x$ axis ($\alpha$ and $\beta$ must be small). |
| Wing is divided into panels. | Chords length, sweep/dihedral angles, twist that vary along span can be defined. |

$\beta$ -- sideslip angle

### 2.3 User Guide

#### 2.3.1 Introduction

AVL is a free software and can be downloaded from its official website. There is also a guide explaining in details how to use the program (Drela and Youngren, 2010). All, what Windows users have to do, is downloading the file: *AVL 3.35 executable for Windows*. Currently 3.35 is the latest version and this is the one used in this project. After downloading, AVL is ready to use, without need of installation. All the input files must be created in the text editor. They are:

*filename.avl* -- describes geometry.
*filename.mass* -- is obligatory if stability analysis is performed. It includes mass distribution, gravity acceleration and air density in proper units.
*filename.run* -- contains description of run cases. However, this file is not necessary. Those cases can also be entered by writing proper commands inside the program.

An input for calculating minimum induced drag (to determine the circulation), is the lift coefficient and the aircraft geometry. Air density or air speed are not needed. Therefore, analysis performed in this project do not require mass and run files. Sample input files, containing geometry of the wings, are presented in chapter 2.3.2, 3.3 and 4.3.

#### 2.3.2 Creating Geometry - Input File

Another source of information for Chapter 2.3.2 is (Jan, 2015).

Coordinate system used in AVL is:

X downstream; Y out the right wing; Z up

Input geometry file will be explained on a following basic example. It is a tapered wing, without defined profile.

Symbol `#` starts a comment.

```
Oswald_A5
#The title.

#Mach
0.0
#It is possible to add Prandtl-Glauert correction. However, for low velocities it is
#recommended to put zero here.

#IYsym  IZsym   Zsym
 0      0       0.0
# (Anti)symmetry around Y=0 or Z=Zsym can be created. Then forces are calculated only for
#half of the geometry. Although such case requires less calculation, it is rarely used, as
#usually there are not symmetric aerodynamic forces. Value 0 stands for no symmetry, 1 for
#symmetry, -1 for antisymmetry

#Sref   Cref    Bref
32.4    2.640   12.728
#Sref - reference area of the wing, used to define all coefficients: C_L, C_D, C_m
#Cref - reference chord to define pitching moment coefficient: C_m
#Bref - reference span to define roll, yaw moments. (Used also to calculate Oswald factor.)

#Xref   Yref    Zref
1.169   0.0     0.0
#Points on axis used to define moments.

#CDdp
0.020
#A command used in order to add profile drag to calculated induced drag. Then total drag is
#a sum of both of these.
#=====================================================================
SURFACE
#A command to create a lifting surface.

Wing
#A name of the surface.
#Nchordwise  Cspace  Nspanwise  Sspace
8            1.0     12         -2.0
# Number of vortices: Nchordwise, Nspanwise. Entering the number of vortices along span is
# optional. It can be defined here or later in SECTION part - it is possible that each
# section has its own number of vortices. Cspace and Sspace define a type of distribution
# of vortices. It will get described later.

COMPONENT
4
#In case the wing consists of more surfaces than one, a command: COMPONENT is used.
#Then all surfaces with the same number (e.g. 4) are grouped together. It is used to
# e.g. model a wing with winglets or a box wing.

YDUPLICATE
0.0
#An optional command to create geometry that is symmetrical around Ydupl=y. Here: around
#y=0. Remarks: This command 1) does not assume any aerodynamic symmetry. Calculations
#for each part are performed separately. 2) cannot be used when IYsym =1 or =-1

#SCALE, TRANSLATE - optional commands that are used to change dimension or location
#of the whole surface

ANGLE
0.0
#Optional command to change an incidence angle (around spanwise axis) of the whole surface.
#The unit of the angle is degree. Positive value corresponds to a higher angle of attack
#seen by a profile.

#NOWAKE, NOALBE, NOLOAD - optional commands to specify different, more complicated
#cases such as: wind tunnel walls, formation flight etc.
#=====================================================================

SECTION
#Here sections are defined. A chord and an incidence angle will be linearly interpolated
#between them. Therefore, at least two of them must be defined.

#Xle    Yle    Zle    Chord   Ainc    Nspanwise  Sspace
0.      0.     0.     3.394   0.0     0          0
#Xle, Yle, Zle - coordinates of an airfoil's leading edge.
#Chord - chord length. Airfoils are directed along x axis.
#Ainc - to change incidence angle of a specific profile. If two sections have defined
#different Ainc, an incidence angle will change between them as a result of linear function.
#Nspanwise - optional place to define vortices distribution, especially when a particular
#number of vortices between different sections is expected.
#=====================================================================

SECTION
#Xle    Yle    Zle    Chord   Ainc    Nspanwise  Sspace
0.849   6.364  0.     1.697   0.0     0          0
#A definition of the second section.
#=====================================================================
```

Possible Vortex Lattice spacing distribution is presented in Figure 2.10. Parameters *Cspace* and *Space* define how vortex panels are distributed between sections. For most of the cases, the cosine distribution across the whole span and the whole chord is recommended. That is because tight distribution is needed for leading and trailing edges and in places, where circulation changes rapidly, e.g. at the tips of the wing. Instead of using cosine on the whole span, a sine on half of the wing can be used.

**Figure 2.10** Possible distribution of vortices in AVL (Drela and Youngren, 2010).

A profile data can be additionally attached. If not, a wing will be created as a flat surface.
AIRFOIL is used to add airfoil data by coordinates $x/c$, $y/c$. AVL will use airfoil camber.
AFILE is used to import airfoil shape from a file generated by another program, e.g. Xfoil.

A command CLAF is used to better represent the lift characteristics of thick airfoils. If not applied, by default AVL sets $C_L/\alpha = 2\pi$ -- this value comes from a thin-airfoil theory.

There is possibility to design the empennage, ailerons and the fuselage. However, these elements do not concern a topic of this project.

#### 2.3.3 Instruction -- Running Program and Accessing Results

In the following instruction '$\rightarrow$' is used for pressing 'enter'.

Remarks:
- Use '$\rightarrow$' to execute a command, enter the value or come back to the previous menu.
- AVL does not recognize small and capital letters.
- In AVL points are used (not commas) for decimal fractions.

Start AVL. You will see the same window as in Figure 2.11.

**Figure 2.11** Starting Window Menu -- AVL.

To load geometry, type command:
`load` $\rightarrow$ `.../filename.avl`(full directory) $\rightarrow$

If you want to see geometry, write:
`oper` $\rightarrow$ `g` $\rightarrow$

Geometry will appear in a new window (Figure 2.12). Remark: even if $\alpha_i$ was changed in geometry file, it will not be visible in geometry plot. It is set as aerodynamic parameter.

**Figure 2.12** Displayed geometry of the wing -- AVL.

This is a trapezoidal wing of $A = 6$ and $\lambda = 0.5$. It is created by two sections and command Yduplicate. Vortices representing wing are distributed between this two sections on a flat surface and then symmetry along $y = 0$ is created.

$A$ -- aspect ratio. It is defined by Equation 2.13.
$\lambda$ -- taper ratio. It is defined by Equation 2.14.

$$A = \frac{b^2}{S} \tag{2.13}$$

$$\lambda = \frac{c_t}{c_r} \tag{2.14}$$

Now run parameters must be specified. Press $\rightarrow$ in a command window in order to exit geometry menu and come back to the oper menu (Figure 2.13).

**Figure 2.13** Oper Menu Window -- AVL.

It includes a list of variables and constraints placed at the top of the window. From the list, choose the variable that you want to set. In my project I want to calculate induced drag and Oswald factor. To do this, the only parameter that must be specified is the angle of attack. In AVL it is called *Alpha*. In the menu we can see that a corresponding letter is *a*. Therefore, we type:
`a` $\rightarrow$

Another list appears (Figure 2.14).

**Figure 2.14** Window to set constraints of the case -- AVL.

A given value of an angle of attack can be entered or specified by a different parameter. We can demand that $\alpha$ causes a specific value of $C_L$, e.g. $C_L = 0.45$ or any other value. Depending on what our conditions are, we type a proper letter. Here as an example:
`c` $\rightarrow$ `0.45` $\rightarrow$

We can also put this command in only one line:
`a c 0.45` $\rightarrow$

Where *a* is a variable and *c* is a constraint. Spaces between letters are obligatory.

To execute calculations for selected case, type:
`x` $\rightarrow$

AVL starts calculations. The time, which it takes, depends on the number of panels the wing is divided into. Enlarge window or scroll back a little to see the results (Figure 2.15).

**Figure 2.15** Window with results -- AVL.

We can see that the wing consist of two surfaces -- we have used a function YDUPLICATE. Total number of strips is 24. 12 on each surface. Total number of vortices is $192 = 2 \cdot 12 \cdot 8$, where 8 is a number of vortices along a chord. We can see reference values, which we defined before and a description of the coordinate system. After that, the results come: Oswald factor, angle of attack, lift, induced drag and pitching moment coefficients.

$C_L$ and $C_D$ with index *ff* are values obtained in Trefftz Plane. They differ a little from $C_{L,tot}$ and $C_{D,ind}$ obtained from the wing surface. Both $C_{D,ff}$ and $C_{D,ind}$ refers to induced drag. If we added profile drag in geometry file, $C_{D,tot}$ (a total drag) would differ from the induced drag.

We can also see lift components in $x$, $y$, $z$ axis: $C_{X,tot}$, $C_{Y,tot}$, $C_{Z,tot}$. $C_{Z,tot}$ is a consequence of *Alpha* being different from 0. $C_{Y,tot} = 0$ is a consequence of $Beta = 0$. The constraint was $C_L = 0.45$. This got realised by setting $Alpha = 6.36573°$.

$e$ - Oswald factor, was calculated from $C_{L,ff}$ and $C_{D,ff}$ and equals 0.9987. Other results would be important in stability analysis.

To see a plot, type (Figure 2.16):
`t` $\rightarrow$

**Figure 2.16** Tapered wing. Trefftz Plot -- results for sine vortex distribution -- AVL.

The gap in a graph is a result of the way we defined geometry -- two surfaces, each with sine distribution. It does not bother us, because we do not expect any discontinuity on a centerline of the wing. To compare, I built the same wing with three sections creating one surface and a cosine vortices distribution along span. That is the result (Figure 2.17).

**Figure 2.17** Trefftz Plot results for cosine vortex distribution -- AVL.

Horizontal axis represents a span in metres. Center line is a center axis of the wing. Blue plot represents induced angle -- $\alpha_i$ changing along the span. At the tip, where $V_{ind}$ is the biggest, there is the biggest absolute value of $\alpha_i$. Minus means it reduces effective angle of attack. A distribution of lift coefficient along span can also be observed. AVL shows three different plots: $C_l$ -- yellow, $C_{lT}$ -- red and $C_l \cdot c/c_{ref}$ -- green.

Definition from AVL instruction (Drela and Youngren, 2010) consists of Equations (2.15), (2.16), (2.17):

$$C_l = \frac{2\,L'}{\rho V_\infty^2 c} \sim \frac{2\Gamma}{V c} \tag{2.15}$$

$$C_{lT} = \frac{2L'}{\rho V_{\infty T}^2 c} \tag{2.16}$$

$$C_l \frac{c}{c_{ref}} = \frac{2\,L'}{\rho V_\infty^2 c_{ref}} \tag{2.17}$$

$L'$ = is a sum along the chord of $[\rho\,\Gamma\,V \times l]$
$V_{\infty T} = V \cos(sweep)$

The difference between $C_l$ and $C_{lT}$ is that $C_{lT}$ takes into account a sweep of the wing. The yellow plot informs us what is the $C_l$ of each section, so that we know, where the stall starts. The green plot is *lift/span loading* $L'$. It says what is a contribution in creating overall lift from each section.

Above the plot other results are displayed. Sometimes different indexes than in previous window (Figure 2.15) are used. These is how they are described in Trefftz Plot:

$\alpha$ -- the angle of attack
$C_L$ -- lift coefficient calculated over the wing surface
$C_D$ -- induced drag coefficient calculated over the wing surface

---

## 3 Oswald Factor

### 3.1 Introduction

Drag of the wing consists of two components:
$C_{D,0}$ -- zero-lift drag
$C_{D,i}$ -- drag due to the lift, caused by downwash.

To estimate the second one, Oswald factor is needed, sometimes called *span efficiency factor*. Usually in preliminary sizing, typical values of $e$ are chosen in order to shorten calculations. However, every shape of the wing has its adequate value. The aim of this chapter is to find out whether AVL can be used to obtain reliable Oswald factor. For this purpose I will examine rectangular and tapered wings and compare the results with theoretical formulas.

### 3.2 Theoretical Background

Equation (3.1) to calculate absolute Oswald factor includes theoretical Oswald factor -- $e_{theo}$ and correction factors describing effect of fuselage -- $k_{e,F}$, viscous drag -- $k_{e,D0}$ and compressibility effects -- $k_{e,M}$.

$$e = e_{theo} \, k_{e,F} \, k_{e,D_0} \, k_{e,M} \tag{3.1}$$

One of the constraints while using AVL is that the flow is inviscid. Therefore it can only calculate $e_{theo}$. What does actually $e$ stand for? Here is Equation (3.2) (Kroo, 2007b) to calculate drag from its distribution along span.

$$D_i = \int_{span} d(y) \, dy = \frac{1}{q \pi b^2} \sum_n n A_n^2 \tag{3.2}$$

It can be compared with another Equation (3.3) (Kroo, 2007b) for total induced drag.

$$D_i = \frac{L^2}{q \pi b^2 e} \tag{3.3}$$

According to (3.4) (Kroo, 2007b), $e$ stands for:

$$e = \frac{L^2}{\sum_n n A_n^2} \tag{3.4}$$

After analyzing following formulas, one of the conclusions is that a minimum induced drag responds to constant downwash speed (Kroo, 2007b). This happens for an elliptical wing. That is why it is considered as an ideal and reference shape. For this case Oswald factor is set $e = 1$. Other shapes of wings usually have $e < 1$ and some higher induced drag. However, trapezoidal wing has similar Oswald factor to elliptical one and at the same time, it is much easier to manufacture. That is why there were very few planes with elliptical wings, the best known -- Supermarine Spitfire. Equation (3.5) describes induced drag coefficient.

$$c_{D,i} = \frac{c_L^2}{\pi A e} \tag{3.5}$$

There are different methods to calculate Oswald factor. I will focus on Equations (3.6), (3.8) (Nita and Scholz, 2012), which describe curve $f(\lambda)$ derived by Hoerner.

$$e_{theo} = \frac{1}{1 + f(\lambda) \cdot A} \tag{3.6}$$

$$f(\lambda) = \frac{1 - e_{theo}}{e_{theo} \cdot A} \tag{3.7}$$

$$f(\lambda) = 0{,}0524\,\lambda^4 - 0{,}15\,\lambda^3 + 0{,}1659\,\lambda^2 - 0{,}0706\,\lambda + 0{,}0119 \tag{3.8}$$

Here, theoretical span efficiency factor depends only on geometry: taper ratio and aspect ratio. Hoerner's equation includes a function (3.8) that depends only on taper ratio, multiplied later by aspect ratio. It is also important to notice that Equation (3.5) for induced drag coefficient also contains $A$ in denominator. It means when $A$ grows, $C_{D,i}$ gets smaller. However, when $A$ grows, $e_{theo}$ also gets smaller. Obviously when $e_{theo}$ gets smaller, $C_{D,i}$ grows. All in all, $C_{D,i}$ gets smaller with growing $A$, but not linearly.

Figure 3.1 is a plot representing Hoerner's function $f(\lambda)$. When the function reaches its minimum, $e_{theo}$ is the highest. Hence, an optimum value of taper ratio is $\lambda_{opt} = 0{,}357$.

**Figure 3.1** Induced drag depends on taper ratio. This relationship can be described with function $f(\lambda)$. It indicates an optimum value of taper ratio of the wing (Hoerner, 1992).

In AVL the span efficiency is calculated from $C_D$ and $C_L$ from Trefftz Plane. Equation (3.9) is a definition from the AVL website:

$$e = \frac{C_L^2 + C_Y^2}{\pi A C_{D,i}} \tag{3.9}$$

$$A = \frac{B_{ref}^2}{S_{ref}} \tag{3.10}$$

Where $S_{ref}$ is replaced by $2 \cdot S_{ref}$ for Y-image cases ($iYsym = 1$).

### 3.3 AVL - Input Method

All wings will be examined in the same flight conditions.
$\rho = 1{,}225$ kg/m$^3$ -- air density,
$g = 9{,}81$ m/s$^2$ -- gravitational acceleration
$V_\infty = 22$ m/s -- air speed
$m = 464$ kg -- mass of the wing
$S = 32{,}4$ m$^2$ -- wing area

In steady flight lift (3.11) is equal to weight (3.12).

$$L = \frac{1}{2} \rho V_\infty^2 S \, c_L \tag{3.11}$$

$$Q = mg \tag{3.12}$$

$Q$ -- wing weight

Lift coefficient of the wings is calculated by comparing these well-known formulas.

$C_L = 0{,}4739$ -- lift coefficient.

What will vary between different wings is: aspect ratio, taper ratio and as a result: chords and span. Following cases will be examined:

| Wing type | Taper ratio | Aspect ratio |
|-----------|-------------|--------------|
| Rectangular wing | $\lambda = 1$ | $A$ -- variable |
| Trapezoidal wing | $\lambda_{opt} = 0{,}357$ | $A$ -- variable |
|  | $\lambda$ -- variable | $A = 5$ |
|  | $\lambda$ -- variable | $A = 10$ |
|  | $\lambda$ -- variable | $A = 20$ |

Figure 3.3 is an input file for a wing with $A = 10$. Equation (2.13) is used to calculate span $b$. A chord of a rectangular wing is calculated from (3.13):

$$c = \frac{S}{b} \tag{3.13}$$

Equations (2.14) and (3.14) determine root and tip chords.

$$S = \frac{1}{2}(c_r + c_t) b \tag{3.14}$$

I start with the least complicated shape -- a rectangular wing of $A = 10$ (Figure 3.2).

**Figure 3.2** An explanatory geometry input file. It is a compulsory file to perform analysis in AVL. Here, it describes a rectangular wing of aspect ratio $A = 10$.

**Figure 3.3** Geometry displayed in AVL. Here, this is a rectangular wing of $A = 10$. Violet stripes represent distributed vortices.

I set an angle of attack so that $C_L = 0{,}4739$ and run program:
`oper` $\rightarrow$ `a` $\rightarrow$ `c 0.4739` $\rightarrow$ `x` $\rightarrow$

Afterwards, I write another input files with different $A$ and do the same procedure. I collect all results in adequate tables in Excel file. Figures 3.4, 3.5, 3.6 present input and geometry files.

**Figure 3.4** Geometry input file describing the wing of $A = 20$, $\lambda = 0{,}2$ -- AVL.

**Figure 3.5** Geometry of the tapered wing displayed in AVL. Wing parameters: $A = 20$, $\lambda = 0{,}2$.

**Figure 3.6** Geometry of the tapered wing displayed in AVL. Wing parameters: $A = 10$, $\lambda_{opt} = 0{,}357$.

### 3.4 AVL -- Output Analysis

First I will have a look into output from Trefftz Plot: lift distribution, induced angle and some coefficients. Figures 3.7, 3.8, 3.9 present Trefftz Plots of different cases.

In Figure 3.7 there is noticeable downwash at the tips of the wing, $\alpha_i$ is around $-0{,}07°$.

**Figure 3.7** Trefftz Plot illustrating lift distribution and induced angle over the wing span. Results for wing parameters: $A = 10$, $\lambda = 1$ -- rectangular wing.

**Figure 3.8** Trefftz Plot illustrating lift distribution and induced angle over the wing span. Results for wing parameters: $A = 20$, $\lambda = 0{,}2$ -- tapered wing.

Figure 3.8 shows a specific distribution of lift coefficient for tapered wings -- yellow plot.

**Figure 3.9** Trefftz Plot illustrating lift distribution and induced angle over the wing span. Results for wing parameters: $A = 10$, $\lambda_{opt} = 0{,}357$ -- optimally tapered wing.

In Figure 3.9 the wing has typical aspect ratio $A = 10$ and optimum taper ratio $\lambda_{opt} = 0{,}357$ according to (3.8). As a consequence, it has smaller $\alpha_i$ than for rectangular wing of the same $A$. At the tip it is around $-0{,}05°$.

All the results are gathered in Tables 3.1, 3.2. These are wings of constant $\lambda$ and variable $A$.

**Table 3.1** Comparison of results obtained by AVL and by theoretical formulas. Case 1: aspect ratio: variable, taper ratio: constant $\lambda = 1$ -- rectangular wing.

| $A$ | | AVL | | | | | THEORETICAL | | | | ERRORS (%) | |
|-----|---|-----|---|---|---|---|-------------|---|---|---|------------|---|
| | $\alpha$ | $e$ | $C_{D,ff}$ | $C_{L,ff}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ |
| 5 | 6.91 | 0.9892 | 0.01456 | 0.47565 | 0.0022 | | 0.9542 | 0.01498 | 0.0096 | | 3.54 | -2.83 | -77.25 |
| 7 | 6.17 | 0.9779 | 0.01049 | 0.47503 | 0.0032 | | 0.9370 | 0.01090 | 0.0096 | | 4.18 | -3.75 | -66.37 |
| 9 | 5.77 | 0.9656 | 0.00825 | 0.47473 | 0.0040 | | 0.9205 | 0.00863 | 0.0096 | | 4.67 | -4.40 | -58.77 |
| 10 | 5.63 | 0.9594 | 0.00747 | 0.47463 | 0.0042 | | 0.9124 | 0.00784 | 0.0096 | | 4.90 | -4.66 | -55.92 |
| 11 | 5.52 | 0.9531 | 0.00684 | 0.47456 | 0.0045 | | 0.9045 | 0.00719 | 0.0096 | | 5.10 | -4.80 | -53.40 |
| 13 | 5.34 | 0.9413 | 0.00586 | 0.47445 | 0.0048 | | 0.8890 | 0.00619 | 0.0096 | | 5.55 | -5.26 | -50.03 |
| 15 | 5.21 | 0.9299 | 0.00514 | 0.47437 | 0.0050 | | 0.8741 | 0.00545 | 0.0096 | | 6.00 | -5.72 | -47.65 |

**Table 3.2** Comparison of results obtained by AVL and by theoretical formulas. Case 2: aspect ratio: variable, taper ratio: constant $\lambda_{opt} = 0{,}357$.

| $A$ | | AVL | | | | | THEORETICAL | | | | ERRORS (%) | |
|-----|---|-----|---|---|---|---|-------------|---|---|---|------------|---|
| | $\alpha$ | $e$ | $C_{D,ff}$ | $C_{L,ff}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ |
| 5 | 6.68 | 0.9984 | 0.01411 | 0.47555 | 0.0003 | | 0.9908 | 0.01443 | 0.0019 | | 0.77 | -2.22 | -82.82 |
| 7 | 5.95 | 0.9967 | 0.01029 | 0.47495 | 0.0005 | | 0.9871 | 0.01035 | 0.0019 | | 0.96 | -0.54 | -74.65 |
| 9 | 5.57 | 0.9946 | 0.00801 | 0.47467 | 0.0006 | | 0.9835 | 0.00808 | 0.0019 | | 1.12 | -0.82 | -67.67 |
| 10 | 5.43 | 0.9934 | 0.00722 | 0.47458 | 0.0007 | | 0.9817 | 0.00728 | 0.0019 | | 1.18 | -0.85 | -64.39 |
| 11 | 5.33 | 0.9921 | 0.00657 | 0.47390 | 0.0007 | | 0.9799 | 0.00663 | 0.0019 | | 1.23 | -0.94 | -61.20 |
| 13 | 5.17 | 0.9897 | 0.00557 | 0.47440 | 0.0008 | | 0.9763 | 0.00563 | 0.0019 | | 1.35 | -1.11 | -57.09 |
| 15 | 5.05 | 0.9871 | 0.00484 | 0.47432 | 0.0009 | | 0.9728 | 0.00490 | 0.0019 | | 1.45 | -1.21 | -53.31 |

Equation (3.15) was used to measure all the errors.

$$error = \frac{AVL - Theory}{Theory} \cdot 100\% \tag{3.15}$$

AVL seems to provide very good results. Plots in Figures 3.10 and 3.11 show the same tendency: Oswald factor and $D_i$ gets smaller when $A$ grows. It should be remembered that in (3.5) both $e$ and $A$ are located in denominator.

**Figure 3.10** Plots showing relationship between Oswald factor and aspect ratio. One is based on results from AVL, another one on theoretical formulas. Wing parameter: constant taper ratio $\lambda_{opt} = 0{,}357$ -- optimally tapered wing.

**Figure 3.11** Plots showing relationship between induced drag and aspect ratio. One is based on results from AVL, another one on theoretical formulas. Wing parameter: constant taper ratio $\lambda_{opt} = 0{,}357$ -- optimally tapered wing.

For optimum $\lambda$ according to (3.8), error between $e$ calculated in AVL and by (3.6) is smaller than 1.5 %. When it comes to induced drag, the biggest value is for $A = 5$. In Figure 3.11 it is the only point, in which we can easily distinguish red and green colors. For bigger $A$, both curves are almost on top of each other, as the error between them is around 1%. However, starting from $A = 7$, the error grows as $A$ grows. For rectangular wing error of both $e$ and $C_{D,i}$ is smaller than 6%. The tendency seems to be that the smaller $A$, the better accuracy of $e$ and $D_i$ (Figure 3.14, 3.15). Also, as it has been expected, the rectangular wing induces more drag than optimally tapered one, between 3 % -6 %, according to results from AVL.

However, one thing about the result is unexpected. Figures 3.12, 3.13 show plots of $f(\lambda)$. Equation (3.8) is supposed to be independent from $A$. It should only measure influence of $\lambda$. Hence, for $\lambda$ -- constant, Equation (3.8) should have only one solution. I built a theoretical plot from Hoerner equation and another one by using (3.7) and results -- Oswald factor -- from AVL. The difference between results is very big: between 45 % and 85 %, and it is higher for low aspect ratio. Moreover, $f(\lambda)$ from AVL is an increasing function, not constant!

**Figure 3.12** Plots showing relationship between function $f(\lambda)$ and aspect ratio. One is based on results from AVL, another one on theoretical formulas. In theory, both should be horizontal lines, since $f(\lambda)$ depends only on $\lambda$. Wing parameter: constant taper ratio $\lambda_{opt} = 0{,}357$ -- optimally tapered wing.

**Figure 3.13** Plots showing relationship between function $f(\lambda)$ and aspect ratio. One is based on results from AVL, another one on theoretical formulas. In theory, both should be horizontal lines, since $f(\lambda)$ depends only on $\lambda$. Wing parameter: constant taper ratio $\lambda = 1$ -- rectangular wing.

**Figure 3.14** Plots showing relationship between errors (Oswald factor, induced drag, $f(\lambda)$) and aspect ratio. Errors tell how results obtained in AVL differ from theory. Wing parameter: constant taper ratio $\lambda_{opt} = 0{,}357$ -- optimally tapered wing.

**Figure 3.15** Plots showing relationship between errors (Oswald factor, induced drag, $f(\lambda)$) and aspect ratio. Errors tell how results obtained in AVL differ from theory. Wing parameter: constant taper ratio $\lambda = 1$ -- rectangular wing.

Now I will take closer look at wings of constant $A$ and $\lambda$ changing from 0 to 1. The results are gathered in Table 3.3 and Table 3.4.

**Table 3.3** Comparison of results obtained by AVL and by theoretical formulas. Case 3: taper ratio: variable, aspect ratio: constant $A = 5$.

| $\lambda$ | | AVL | | | | | THEORETICAL | | | | ERRORS (%) | |
|---|---|-----|---|---|---|---|-------------|---|---|---|------------|---|
| | $\alpha$ | $e$ | $C_{D,ff}$ | $C_{L,ff}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ |
| 0 | 7.08 | 0.9293 | 0.01551 | 0.47578 | 0.0152 | | 0.9438 | 0.01515 | 0.0119 | | -1.56 | 2.39 | 27.86 |
| 0.1 | 6.80 | 0.9800 | 0.01469 | 0.47561 | 0.0041 | | 0.9692 | 0.01475 | 0.0064 | | 1.10 | -0.42 | -35.77 |
| 0.15 | 6.75 | 0.9879 | 0.01458 | 0.47558 | 0.0024 | | 0.9777 | 0.01462 | 0.0046 | | 1.03 | -0.30 | -46.32 |
| 0.2 | 6.71 | 0.9926 | 0.01451 | 0.47557 | 0.0015 | | 0.9838 | 0.01453 | 0.0033 | | 0.89 | -0.16 | -54.81 |
| 0.3 | 6.68 | 0.9973 | 0.01444 | 0.47555 | 0.0005 | | 0.9900 | 0.01444 | 0.0020 | | 0.73 | -0.02 | -73.27 |
| 0.357 | 6.68 | 0.9984 | 0.01442 | 0.47555 | 0.0003 | | 0.9908 | 0.01443 | 0.0019 | | 0.77 | -0.08 | -82.82 |
| 0.4 | 6.69 | 0.9989 | 0.01441 | 0.47556 | 0.0002 | | 0.9904 | 0.01444 | 0.0019 | | 0.85 | -0.18 | -88.68 |
| 0.5 | 6.71 | 0.9987 | 0.01442 | 0.47557 | 0.0003 | | 0.9872 | 0.01448 | 0.0026 | | 1.15 | -0.44 | -89.99 |
| 0.6 | 6.74 | 0.9977 | 0.01443 | 0.47558 | 0.0005 | | 0.9821 | 0.01456 | 0.0037 | | 1.57 | -0.88 | -87.39 |
| 0.8 | 6.82 | 0.9940 | 0.01449 | 0.47561 | 0.0012 | | 0.9697 | 0.01474 | 0.0063 | | 2.45 | -1.73 | -80.71 |
| 1 | 6.86 | 0.9917 | 0.01452 | 0.47563 | 0.0017 | | 0.9626 | 0.01485 | 0.0078 | | 2.93 | -2.24 | -78.45 |

**Table 3.4** Comparison of results obtained by AVL and by theoretical formulas. Case 4: taper ratio: variable, aspect ratio: constant $A = 10$.

| $\lambda$ | | AVL | | | | | THEORETICAL | | | | ERRORS (%) | |
|---|---|-----|---|---|---|---|-------------|---|---|---|------------|---|
| | $\alpha$ | $e$ | $C_{D,ff}$ | $C_{L,ff}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ |
| 0 | 5.66 | 0.8748 | 0.0082 | 0.4747 | 0.0143 | | 0.8937 | 0.00800 | 0.0119 | | -2.16 | 2.51 | 20.27 |
| 0.1 | 5.50 | 0.9525 | 0.00753 | 0.4746 | 0.0050 | | 0.9403 | 0.00760 | 0.0064 | | 1.29 | -0.96 | -21.52 |
| 0.15 | 5.47 | 0.9696 | 0.00739 | 0.4746 | 0.0031 | | 0.9564 | 0.00747 | 0.0046 | | 1.37 | -1.14 | -31.29 |
| 0.2 | 5.45 | 0.9804 | 0.00731 | 0.4746 | 0.0020 | | 0.9681 | 0.00738 | 0.0033 | | 1.26 | -1.01 | -39.42 |
| 0.3 | 5.43 | 0.9912 | 0.00723 | 0.4746 | 0.0009 | | 0.9801 | 0.00729 | 0.0020 | | 1.12 | -0.87 | -56.17 |
| 0.357 | 5.43 | 0.9934 | 0.00722 | 0.4746 | 0.0007 | | 0.9817 | 0.00728 | 0.0019 | | 1.18 | -0.85 | -64.39 |
| 0.4 | 5.44 | 0.9939 | 0.00721 | 0.4746 | 0.0006 | | 0.9809 | 0.00729 | 0.0019 | | 1.31 | -1.07 | -68.45 |
| 0.5 | 5.46 | 0.9922 | 0.00723 | 0.4746 | 0.0008 | | 0.9747 | 0.00733 | 0.0026 | | 1.77 | -1.43 | -69.76 |
| 0.6 | 5.49 | 0.9878 | 0.00726 | 0.4746 | 0.0012 | | 0.9647 | 0.00741 | 0.0037 | | 2.33 | -2.03 | -66.21 |
| 0.8 | 5.56 | 0.9750 | 0.00735 | 0.4746 | 0.0026 | | 0.9411 | 0.00760 | 0.0063 | | 3.48 | -3.24 | -59.03 |
| 1 | 5.63 | 0.9594 | 0.00747 | 0.4746 | 0.0042 | | 0.9124 | 0.00784 | 0.0096 | | 4.90 | -4.66 | -55.92 |

**Table 3.5** Comparison of results obtained by AVL and by theoretical formulas. Case 5: taper ratio: variable, aspect ratio: constant $A = 20$.

| $\lambda$ | | AVL | | | | | THEORETICAL | | | | ERRORS (%) | |
|---|---|-----|---|---|---|---|-------------|---|---|---|------------|---|
| | $\alpha$ | $e$ | $C_{D,ff}$ | $C_{L,ff}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ | | $e$ | $C_{D,i}$ | $f(\lambda)$ |
| 0 | 4.98 | 0.8224 | 0.00435 | 0.4743 | 0.0108 | | 0.8078 | 0.00443 | 0.0119 | | 1.78 | -1.70 | -9.26 |
| 0.1 | 4.90 | 0.9177 | 0.00386 | 0.4739 | 0.0045 | | 0.8872 | 0.00403 | 0.0064 | | 3.32 | -4.19 | -29.43 |
| 0.15 | 4.88 | 0.9436 | 0.00379 | 0.4742 | 0.0030 | | 0.9164 | 0.00390 | 0.0046 | | 2.89 | -2.84 | -34.51 |
| 0.2 | 4.87 | 0.9607 | 0.00373 | 0.4742 | 0.0020 | | 0.9381 | 0.00381 | 0.0033 | | 2.35 | -2.11 | -38.02 |
| 0.3 | 4.87 | 0.9773 | 0.00366 | 0.4742 | 0.0012 | | 0.9611 | 0.00372 | 0.0020 | | 1.66 | -1.59 | -42.66 |
| 0.357 | 4.87 | 0.9805 | 0.00365 | 0.4742 | 0.0010 | | 0.9640 | 0.00371 | 0.0019 | | 1.68 | -1.56 | -46.71 |
| 0.4 | 4.87 | 0.9802 | 0.00365 | 0.4742 | 0.0010 | | 0.9625 | 0.00371 | 0.0019 | | 1.80 | -1.71 | -48.08 |
| 0.5 | 4.89 | 0.9743 | 0.00367 | 0.4742 | 0.0013 | | 0.9506 | 0.00376 | 0.0026 | | 2.44 | -2.40 | -49.27 |
| 0.6 | 4.91 | 0.9636 | 0.00371 | 0.4742 | 0.0019 | | 0.9319 | 0.00384 | 0.0037 | | 3.29 | -3.28 | -48.32 |
| 0.8 | 4.96 | 0.9353 | 0.00383 | 0.4742 | 0.0035 | | 0.8887 | 0.00402 | 0.0063 | | 4.98 | -4.77 | -44.74 |
| 1 | 5.01 | 0.9041 | 0.00396 | 0.4743 | 0.0053 | | 0.8389 | 0.00426 | 0.0096 | | 7.21 | -7.06 | -44.75 |

Here, error of $e$ as well as $D_i$ never exceeds 7.5 %. Wings of higher aspect ratio experience higher errors, e.g. for $A = 5$, the errors are around $-1{,}5\%$ -- $3\%$. Moreover, the smallest errors are around $\lambda_{opt}$. Besides, we can observe a typical curve describing Oswald factor, which first grows and after passing an optimum point, it gets smaller. Induced drag behaves exactly opposite way. Plots for wings of aspect ratio 5, 10 and 20 are visible in Figures 3.16, 3.17, 3.18, 3.19, 3.20, 3.21.

**Figure 3.16** Plots showing relationship between Oswald factor and taper ratio. One is based on results from AVL, another one on theoretical formulas. Wing parameter: constant aspect ratio $A = 5$.

**Figure 3.17** Plots showing relationship between Oswald factor and taper ratio. One is based on results from AVL, another one on theoretical formulas. Wing parameter: constant aspect ratio $A = 10$.

**Figure 3.18** Plots showing relationship between Oswald factor and taper ratio. One is based on results from AVL, another one on theoretical formulas. Wing parameter: constant aspect ratio $A = 20$.

**Figure 3.19** Plots showing relationship between induced drag and taper ratio. One is based on results from AVL, another one on theoretical formulas. Wing parameter: constant aspect ratio $A = 5$.

**Figure 3.20** Plots showing relationship between induced drag and taper ratio. One is based on results from AVL, another one on theoretical formulas. Wing parameter: constant aspect ratio $A = 10$.

**Figure 3.21** Plots showing relationship between induced drag and taper ratio. One is based on results from AVL, another one on theoretical formulas. Wing parameter: constant aspect ratio $A = 20$.

When it comes to the plot of $f(\lambda)$, a general shape is preserved, however, values differ. The best resemblance is probably for very small values of $\lambda$ and still close to the optimum of the function. In Figures 3.22, 3.23 and 3.24 plots are created according to results obtained from (3.7) and (3.8) for wing with different $A$: 5, 10, 20.

**Figure 3.22** Plots showing relationship between function $f(\lambda)$ and taper ratio. One is based on results from AVL, another one on theoretical formulas. Polynomial function were created in order to find a formula best fitting function from AVL. These are 4th (as Hoerner polynomial) and 6th (better resemblance) polynomials. Wing parameter: constant aspect ratio $A = 5$.

**Figure 3.23** Plots showing relationship between function $f(\lambda)$ and taper ratio. One is based on results from AVL, another one on theoretical formulas. Polynomial function were created in order to find a formula best fitting function from AVL. These are 4th (as Hoerner polynomial) and 6th (better resemblance) polynomials. Wing parameter: constant aspect ratio $A = 10$.

**Figure 3.24** Plots showing relationship between function $f(\lambda)$ and taper ratio. One is based on results from AVL, another one on theoretical formulas. Polynomial function were created in order to find a formula best fitting function from AVL. These are 4th (as Hoerner polynomial) and 6th (better resemblance) polynomials. Wing parameter: constant aspect ratio $A = 20$.

To compare errors for two extreme cases: aspect ratio 5 and 20, I put Figures 3.25 and 3.26.

**Figure 3.25** Plots showing relationship between errors (Oswald factor, induced drag, $f(\lambda)$) and taper ratio. Errors tell how results obtained in AVL differ from theory. Wing parameter: constant aspect ratio $A = 5$.

**Figure 3.26** Plots showing relationship between errors (Oswald factor, induced drag, $f(\lambda)$) and taper ratio. Errors tell how results obtained in AVL differ from theory. Wing parameter: constant aspect ratio $A = 20$.

Here, similarly as in previous case, the highest error refers to $f(\lambda)$. At the end, the error of the $D_i$ and $e$ is at satisfactory low level. However, in the behaviour of $f(\lambda)$ a very interesting relationship occurred again: the error gets smaller as $A$ gets bigger. This idea is based on 3 different $A$: 5, 10 and 20. It is recommended to do more analysis of the wings with extremely high aspect ratio. As it was not planned as a main point of this project, I did not have enough time to create further models.

The hypothesis is: would error of $f(\lambda) \rightarrow 0$ when $A \rightarrow \infty$? If yes, it could mean that Hoerner equation describes a wing of infinite span. If not, maybe we could replace (3.6) and (3.8) with a new, more precise formula.

The first attempt was to calculate optimum values of $f(\lambda)$ from AVL for and $A = 5$, 10, 20.

I used Excel regression function to find polynomial function that provides the best resemblance with the AVL plot. Quite good resemblance was already for 6th polynomial. Then, optimum $\lambda$ was respectively: 0.338; 0.336 and 0.341. I remind that optimum from Hoerner is 0.357. Afterwards, I decided to use 4th polynomial to compare coefficients of Hoerner polynomial (3.8). The results are gathered in Table 3.5 and Figure 3.27.

**Table 3.6** Comparison of coefficients of the 4th polynomial of Hoerner function and $f(\lambda)$ for different aspect ratio.

| $A$ | 4th | 3rd | 2nd | 1st | -- |
|-----|-----|-----|-----|-----|----|
| 5 | 0.1728 | -0.4206 | 0.3598 | -0.1241 | 0.0146 |
| 10 | 0.1429 | -0.3504 | 0.3076 | -0.1097 | 0.0140 |
| 20 | 0.0860 | -0.2186 | 0.2034 | -0.0760 | 0.0106 |
| All (Hoerner) | 0.0524 | -0.1500 | 0.1659 | -0.0706 | 0.0119 |

**Figure 3.27** Relationship between 4th polynomial coefficients (polynomial describing function $f(\lambda)$, which was built on results from AVL) and aspect ratio.

It is very interesting that for these three points, the relationship between all the coefficients is linear. Definitely more cases should be calculated. At this point, it is possible to build polynomials of different orders (based on results from these three values of $A$) and extrapolate the function for higher values of $A$. Different possible plots can be read in Figure 3.28.

**Figure 3.28** Function $f(\lambda)$ as obtained from calculations with AVL for $A = 5$, $A = 10$, and $A = 20$ and represented by an 8th order polynomial. The same function extrapolated to higher aspect ratios $A$ with a 4th order polynomial. For comparison Hoerner's curve is given. It can be seen as an approximation for the upper limit of $f(\lambda)$ (Scholz, 2015a).

The higher order polynomials can be numerically problematic. An 8th order polynomial was used successfully for aspect ratios $A = 5$, $A = 10$, and $A = 20$. The simpler 4th order polynomials worked successfully with extrapolated coefficients for aspect ratios $A$ larger than 20 where no AVL calculations were done.

Hoerner's curve seems to be the limit for high aspect ratios and large $\lambda$. However for small $\lambda$, the largest $f(\lambda)$ are obtained for low aspect ratios. Also here Hoerner's curve predicts quite well largest possible $f(\lambda)$. Together in can be stated that Hoerner's curve is an approximation of the upper limit of $f(\lambda)$. With Hoerner's curve a conservative (rather a little too large) Oswald factor is calculated (Scholz, 2015a).

---

## 4 Box Wing

### 4.1 Introduction

The aim of this part of the project is to assess potential of AVL as a tool to preliminary designing a *box wing*. The emphasis is laid on reliability for different decalage, $h/b$ ratio and angle of attack. Two students have already done some experiments on a box wing model in a wind tunnel, however, the results, that they have received, differ. At the end of this chapter, I will create a plot of the $k$ -- a curve introduced by Prandtl, and compare it with those generated from the wind tunnel.

### 4.2 Theoretical Background

In order to reduce induced drag of the wing, we can increase its aspect ratio or Oswald factor. Increasing $A$ makes wing heavier and bigger. Therefore other solutions are taken into account, e.g. a non-planar wing of much higher $e$. Different modifications have already been created: adding winglets on tips of the wing, *C shape wing* - 'winglets on winglets' or a box wing. The ideas are illustrated in Figure 4.1. All configurations have the same span and total lift. The number is the span efficiency factor. $h/b$ (*vertical distance length/span*) of each case equals 0.2.

**Figure 4.1** Span efficiency for optimally loaded non planar wings with $h/b = 0{,}2$ (Kroo, 2005).

In this project the focus is on a box wing. It consists of two horizontal rectangular wings and vertical rectangular winglets connecting their tips. In this way the induced drag is lowered.

To see the difference in performance of a box wing, it is referenced to the rectangular wing of the same span, total wing surface and (global) aspect ratio.

Important parameters and assumptions based on literature and already performed experiments:

*Span* -- the same for lower and upper wing.
*Reference Area* -- a sum of the area of a lower and upper wing.
*Reference Wing* -- a single rectangular wing of the same area and span as box wing, for this reason, of a twice longer chord.
$h/b$ -- ratio: vertical distance (called also *vertical stagger*) between both wings over their span. The higher $h/b$ ratio, the higher $e$, because wings interfere less with each other. Hence, the best results when $h/b \rightarrow \infty$.
*Decalage* -- an angle between lower and upper wing. It has an influence on lift distribution. Unit: degree. Positive value means that the upper wing is tilted backwards, increasing $\alpha$.
*Horizontal Stagger* -- a horizontal distance between lower and upper wing. According to Munk's Stagger Theorem:

> *"The total induced drag of a system of lifting surfaces is not changed when the elements are moved in the streamwise direction." (Munk, 1923)*

Besides, lift should be distributed equally on both wings in order to get the best *glide ratio*. At the end, glide ratio is the parameter that determines how good the wing is.

Figure 4.2 illustrates tip vortices, which neutralize each other and lift distribution over the horizontal wings and winglets.

**Figure 4.2** On the left, lift distribution on horizontal wings and winglets of the box wing. On the right, counteracting tip vortices (Schiktanz, 2011).

According to Prandtl, two wings (upper and lower) of the same span have the lowest $D_i$. Global $A$ of the box wing is defined by Equation (4.1), where $S_1$ and $S_2$ are areas of the lower and upper wing. The individual aspect ratio -- $A_i$ of each wing is higher than global (Equation 4.2).

$$A = \frac{b^2}{S_1 + S_2} \tag{4.1}$$

$$A_i = \frac{b^2}{S_i} \tag{4.2}$$

Symbol $k$ is used in order to compare performance of the box wing to the reference wing.
$k$ -- called *induced drag factor*, is the ratio between the induced drag they create (4.3).

$$k = \frac{D_{i,BW}}{D_{i,BW,ref}} \tag{4.3}$$

$D_{i,BW}$ -- box wing induced drag
$D_{i,BW,ref}$ -- reference wing induced drag

Between $k$ and $e$ there is a correlation (4.4):

$$\frac{1}{k} = \frac{e_{BW}}{e_{BW,ref}} \tag{4.4}$$

$e_{BW}$ -- box wing Oswald factor
$e_{BW,ref}$ -- reference wing Oswald factor

Equation (4.5) is an equation introduced by Prandtl.

$$k = \frac{k_1 + k_2 \left(\frac{h}{b}\right)}{k_3 + k_4 \left(\frac{h}{b}\right)} \tag{4.5}$$

Parameter $k$ depends on $h/b$ ratio. Many researchers worked on this equation and suggested different values of factors $k_1$, $k_2$, $k_3$ and $k_4$. They are presented in subchapter 4.4 in Table 4.21.

### 4.3 AVL -- Input Geometry of the Box Wing

I start with a simple test to verify results I get from AVL for a box wing configuration. For this purpose I create a box wing without decalage, $\alpha = 6°$, $h/b = 0{,}2$ and calculate $e$. According to Figure 4.1, I expect it should be around 1.46. AVL calculates $e = 1{,}453$. I assume it is a reasonable value.

I proceed to my main task. In text editor I model a box wing of the same parameters as the one examined in a wind tunnel by students.

Reference dimensions:
$S_{BW,ref} = 0{,}104$ m$^2$ -- reference wing area
$A = 2{,}6$
$b = 0{,}52$ m
$c_{BW,ref} = 0{,}2$ m -- reference wing chord
$c_{BW} = 0{,}1$ m -- box wing chord

These are the only parameters that are required by AVL to obtain Oswald factor.

I examine different cases. These are configuration parameters:
$h/b = \{0{,}31;\; 0{,}62;\; 0{,}93\}$
Decalage $= \{-6°;\; -3°;\; 0°;\; 3°;\; 6°;\; 9°\}$ -- an incidence angle of the bottom wing remains $0°$, the one of the upper wing is variable
$\alpha = \{0°, 2°, 4°, 6°, 8°, 10°, 12°, 14°\}$ -- an angle of attack of the bottom wing

Figure 4.3 is a sample geometry input of a case: $h/b = 0{,}31$, decalage $= 6°$. Units: meter, degree.

**Figure 4.3** A sample geometry input of a box wing for AVL. $h/b = 0{,}31$, decalage $= 6°$.

The wing flies with the speed $V = 25{,}45$ m/s. Parameter $S_{BW,ref}$ refers to the total surface of the box wing. Box wing is created with three SURFACE commands. In the first one, two sections create a half of the lower horizontal wing, which is then copied around $y = 0$ and forms the whole horizontal wing. The upper wing is created in the same way. This one is placed at $z = 0{,}1612$. This comes from Equation (4.6), where $b = 0{,}52$ m and $h = 0{,}1612$ m

$$h = 0{,}31 \cdot b \tag{4.6}$$

Command ANGLE is set to 6, which refers to the decalage of the box wing equal to $+6°$. Afterwards, a winglet is designed -- a surface between two sections at the tips of the horizontal wings. Command YDUPLICATE forms the second winglet. Each surface has the same number of vortices and sine distribution. All surfaces are joined together by command COMPONENT=1 and establish one body.

Geometry file is ready. I start AVL and plot a geometry (Figure 4.4).
`load` $\rightarrow$ `<filename.avl>` $\rightarrow$ `oper` $\rightarrow$ `g` $\rightarrow$

**Figure 4.4** Geometry displayed in AVL. Box wing of decalage $= +6°$, $h/b = 0{,}31$. Decalage is not visible in the geometry plot. AVL sets it as an aerodynamic parameter.

I set an angle of attack to $\alpha = 4°$ and run a program:
`oper` $\rightarrow$ `a` $\rightarrow$ `a 4` $\rightarrow$ `x` $\rightarrow$

I put the results into excel sheet I have created. I do this for the whole range of angles of attack. Then I create a geometry for a different $h/b$ ratio and do the same procedure.

### 4.4 AVL -- Output Analysis

Figure 4.5 illustrates results from Trefftz Plot for this case: decalage $= +6°$, $h/b = 0{,}31$, lower wing -- $\alpha = 4°$. Lift distribution an induced angle along span for bottom and upper wing can be seen. They are definitely changing along the span. In both cases effective angle of attack is smaller at the tips. The plot which is less convex describes the lower wing, a more convex one -- the upper wing. Corresponding $C_L$ plots also have less and more rapid drop at the wing tips. Higher values of $C_L$ occur on the upper wing. The reason is that it has much bigger $\alpha$ due to the positive decalage $= +6°$. At the same time, it experiences bigger downwash, which is caused by bigger difference in pressure. Total $C_L$ of the box wing comes from both surfaces and is referenced to the reference surface defined before.

**Figure 4.5** Trefftz Plot -- AVL. Box wing of decalage $= +6°$, $h/b = 0{,}31$. $\alpha = 4°$ -- lower wing. More convex plot refers to the upper wing -- consequence of decalage. Effect of downwash at the tips -- induced angle of attack and drop in $C_L$.

Figures 4.6 and 4.7 exclude an effect of a decalage in lift distribution. They show two plots: box wing of $h/b = 0{,}31$ and 0.93, without decalage and $\alpha$ of lower wing set to $6°$. Here the difference in $C_L$ comes only from experienced downwash. Plot of higher $C_L$ value still refers to the upper wing. However, in this case the difference is small and is caused by induced angle and interference between both wings (Figure 4.6). As $h/b$ ratio grows, wings interfere less and each of them produces similar amount of lift (Figure 4.7).

**Figure 4.6** Trefftz Plot -- AVL. Box wing without decalage, $h/b = 0{,}31$. $\alpha = 6°$ -- lower wing. A difference in $C_L$ on the upper and lower wing due to induced angle and $h/b$ ratio -- interference between them.

**Figure 4.7** Trefftz Plot -- AVL. Box wing without decalage, $h/b = 0{,}93$. $\alpha = 6°$ -- lower wing. Interference between lower and upper wing gets smaller as $h/b$ grows. Hence, both of them produce similar $C_L$.

Results from reference wing and all three values of $h/b$ ratio are collected in Tables 4.1 ... 4.19. Oswald factor varies with different $\alpha$. The biggest error occurs in situation, when lift is zero or close to zero. It is especially evident for a case with no decalage and angle of attack equal to zero. No profile data was attached in geometry input file. In such a case, AVL models the wing as vortices distributed on a flat surface. Consequently, for $\alpha = 0°$, the wing does not produce lift and AVL assumes that $e = 0$. Moreover, it should be kept in mind that AVL does not provide stall characteristics. Having set $\alpha = +40°$, a result becomes an irrational value of $C_L = 3{,}0$. Hence, in order to avoid including unrealistic values in further calculations, some points got removed (in tables their colour is changed into grey) -- points, which refer to stall or zero lift on the bottom or upper wing. This manipulation was based on results obtained by the other student from the wind tunnel.

**Table 4.1** Results obtained in AVL for reference wing, which will be compared with results for different box wing cases.

| $\alpha$ (°) | $e_{BW,ref}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 0.0000 | 0.0000 | 0.0000 | 0.00000 | 0.00000 |
| 2 | 0.9983 | 0.1014 | 0.1015 | 0.00126 | 0.00126 |
| 4 | 0.9983 | 0.2025 | 0.2028 | 0.00503 | 0.00504 |
| 6 | 0.9983 | 0.3027 | 0.3089 | 0.01126 | 0.01133 |
| 8 | 0.9983 | 0.4018 | 0.4046 | 0.01988 | 0.02008 |
| 10 | 0.9983 | 0.4994 | 0.5048 | 0.03078 | 0.03126 |
| 12 | 0.9983 | 0.5951 | 0.6045 | 0.04383 | 0.04481 |
| 14 | 0.9983 | 0.6887 | 0.7033 | 0.05887 | 0.06067 |

**Table 4.2** Results obtained in AVL in order to examine Oswald factor of box wing. Box wing case 1: $h/b = 0{,}31$, decalage $= -6°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.444 | -0.205 | -0.202 | 0.00343 | 0.00348 |
| 2 | 0.669 | -0.072 | -0.071 | 0.00090 | 0.00093 |
| 4 | 0.469 | 0.061 | 0.060 | 0.00104 | 0.00095 |
| 6 | 1.272 | 0.193 | 0.192 | 0.00385 | 0.00353 |
| 8 | 1.470 | 0.325 | 0.323 | 0.00926 | 0.00867 |
| 10 | 1.540 | 0.455 | 0.453 | 0.01717 | 0.01634 |
| 12 | 1.573 | 0.584 | 0.583 | 0.02748 | 0.02650 |
| 14 | 1.591 | 0.710 | 0.713 | 0.04001 | 0.03910 |

**Table 4.3** Results from AVL for box wing case 2: $h/b = 0{,}31$, decalage $= -3°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.444 | -0.101 | -0.100 | 0.00085 | 0.00086 |
| 2 | 0.498 | 0.031 | 0.031 | 0.00026 | 0.00024 |
| 4 | 1.474 | 0.163 | 0.163 | 0.00230 | 0.00220 |
| 6 | 1.574 | 0.295 | 0.294 | 0.00693 | 0.00673 |
| 8 | 1.603 | 0.425 | 0.425 | 0.14070 | 0.01380 |
| 10 | 1.616 | 0.554 | 0.556 | 0.02361 | 0.02338 |
| 12 | 1.623 | 0.680 | 0.685 | 0.03541 | 0.03543 |
| 14 | 1.628 | 0.804 | 0.814 | 0.04931 | 0.04988 |

**Table 4.4** Results from AVL for box wing case 3: $h/b = 0{,}31$, decalage $= 0°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 2 | 1.6450 | 0.1318 | 0.1319 | 0.0013 | 0.0013 |
| 4 | 1.6450 | 0.2630 | 0.2636 | 0.0052 | 0.0052 |
| 6 | 1.6450 | 0.3931 | 0.3950 | 0.0115 | 0.0116 |
| 8 | 1.6450 | 0.5219 | 0.5259 | 0.0203 | 0.0206 |
| 10 | 1.6450 | 0.6488 | 0.6562 | 0.0314 | 0.0321 |
| 12 | 1.6450 | 0.7735 | 0.7857 | 0.0446 | 0.0459 |
| 14 | 1.6450 | 0.8957 | 0.9142 | 0.0598 | 0.0622 |

**Table 4.5** Results from AVL for box wing case 4: $h/b = 0{,}31$, decalage $= +3°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.4433 | 0.0987 | 0.0994 | 0.0008 | 0.0008 |
| 2 | 1.6276 | 0.2297 | 0.2316 | 0.0040 | 0.0040 |
| 4 | 1.6480 | 0.3599 | 0.3635 | 0.0096 | 0.0098 |
| 6 | 1.6522 | 0.4888 | 0.4949 | 0.0176 | 0.0182 |
| 8 | 1.6529 | 0.6161 | 0.6258 | 0.0280 | 0.0290 |
| 10 | 1.6528 | 0.7413 | 0.7558 | 0.0405 | 0.0423 |
| 12 | 1.6524 | 0.8642 | 0.8850 | 0.0550 | 0.0580 |
| 14 | 1.6519 | 0.0984 | 1.0131 | 0.0714 | 0.0761 |

**Table 4.6** Results from AVL for box wing case 5: $h/b = 0{,}31$, decalage $= +6°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.4430 | 0.1955 | 0.1984 | 0.0033 | 0.0033 |
| 2 | 1.5883 | 0.3257 | 0.3308 | 0.0082 | 0.0084 |
| 4 | 1.6276 | 0.0455 | 0.4629 | 0.0156 | 0.0161 |
| 6 | 1.6420 | 0.5825 | 0.5944 | 0.0252 | 0.0263 |
| 8 | 1.6481 | 0.7082 | 0.7251 | 0.0371 | 0.0391 |
| 10 | 1.6509 | 0.8318 | 0.8550 | 0.0510 | 0.0542 |
| 12 | 1.6523 | 0.9527 | 0.9839 | 0.0668 | 0.0717 |
| 14 | 1.6529 | 1.0706 | 1.1115 | 0.0842 | 0.0915 |

**Table 4.7** Results from AVL for box wing case 6: $h/b = 0{,}31$, decalage $= +9°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.4427 | 0.2911 | 0.2974 | 0.0075 | 0.0075 |
| 2 | 1.5604 | 0.4205 | 0.4302 | 0.0141 | 0.0145 |
| 4 | 1.6063 | 0.5484 | 0.5624 | 0.0231 | 0.0241 |
| 6 | 1.6276 | 0.6747 | 0.6939 | 0.0343 | 0.0362 |
| 8 | 1.6385 | 0.7989 | 0.8246 | 0.0476 | 0.0508 |
| 10 | 1.6446 | 0.9206 | 0.9543 | 0.0629 | 0.0678 |
| 12 | 1.6482 | 1.0396 | 1.0828 | 0.0798 | 0.0871 |
| 14 | 1.6503 | 1.1555 | 1.2100 | 0.0984 | 0.1086 |

**Table 4.8** Results from AVL for box wing case 7: $h/b = 0{,}62$, decalage $= -6°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.5877 | -0.2298 | -0.2267 | 0.00396 | 0.00396 |
| 2 | 0.5229 | -0.0809 | -0.0796 | 0.00146 | 0.00148 |
| 4 | 0.3642 | 0.0679 | 0.0675 | 0.00163 | 0.00153 |
| 6 | 1.3731 | 0.2162 | 0.2146 | 0.00443 | 0.00410 |
| 8 | 1.7395 | 0.3634 | 0.3614 | 0.00978 | 0.00919 |
| 10 | 1.8826 | 0.5091 | 0.5077 | 0.01760 | 0.01676 |
| 12 | 1.9516 | 0.6529 | 0.6534 | 0.02773 | 0.02678 |
| 14 | 1.9901 | 0.7943 | 0.7984 | 0.04004 | 0.03921 |

**Table 4.9** Results from AVL for box wing case 8: $h/b = 0{,}62$, decalage $= -3°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.5875 | -0.1134 | -0.1126 | 0.00098 | 0.00098 |
| 2 | 0.0379 | 0.0346 | 0.0344 | 0.00040 | 0.00038 |
| 4 | 1.7420 | 0.1821 | 0.1814 | 0.00242 | 0.00231 |
| 6 | 1.9509 | 0.3288 | 0.3282 | 0.00698 | 0.00676 |
| 8 | 2.0126 | 0.4742 | 0.4746 | 0.01399 | 0.01370 |
| 10 | 2.0396 | 0.6180 | 0.6204 | 0.02334 | 0.02310 |
| 12 | 2.0541 | 0.7595 | 0.7654 | 0.03489 | 0.03492 |
| 14 | 2.0630 | 0.8986 | 0.9095 | 0.04847 | 0.04909 |

**Table 4.10** Results from AVL for box wing case 9: $h/b = 0{,}62$, decalage $= 0°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 0.0000 | 0.0000 | 0.0000 | 0.00000 | 0.00000 |
| 2 | 2.0948 | 0.1469 | 0.1471 | 0.00127 | 0.00126 |
| 4 | 2.0948 | 0.2932 | 0.2939 | 0.00505 | 0.00505 |
| 6 | 2.0948 | 0.4383 | 0.4404 | 0.01128 | 0.01134 |
| 8 | 2.0948 | 0.5820 | 0.5864 | 0.01985 | 0.02010 |
| 10 | 2.0948 | 0.7237 | 0.7317 | 0.03065 | 0.03129 |
| 12 | 2.0948 | 0.8630 | 0.8760 | 0.04351 | 0.04485 |
| 14 | 2.0948 | 0.9997 | 1.0193 | 0.05826 | 0.06072 |

**Table 4.11** Results from AVL for box wing case 10: $h/b = 0{,}62$, decalage $= +3°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.5869 | 0.1110 | 0.1118 | 0.00096 | 0.00096 |
| 2 | 2.0137 | 0.2569 | 0.2589 | 0.00401 | 0.00407 |
| 4 | 2.0773 | 0.4018 | 0.4056 | 0.00949 | 0.00970 |
| 6 | 2.0943 | 0.5453 | 0.5518 | 0.01731 | 0.01780 |
| 8 | 2.1001 | 0.6872 | 0.6974 | 0.02736 | 0.02835 |
| 10 | 2.1023 | 0.8269 | 0.8421 | 0.03951 | 0.04130 |
| 12 | 2.1030 | 0.9640 | 0.9858 | 0.05359 | 0.05658 |
| 14 | 2.1031 | 1.0983 | 1.1283 | 0.06942 | 0.07411 |

**Table 4.12** Results from AVL for box wing case 11: $h/b = 0{,}62$, decalage $= +6°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.5867 | 0.2204 | 0.2234 | 0.00385 | 0.00385 |
| 2 | 1.9087 | 0.3651 | 0.3705 | 0.00863 | 0.00880 |
| 4 | 2.0138 | 0.5086 | 0.5171 | 0.01573 | 0.01625 |
| 6 | 2.0569 | 0.6505 | 0.6631 | 0.02508 | 0.02617 |
| 8 | 2.0775 | 0.7905 | 0.8082 | 0.03654 | 0.03850 |
| 10 | 2.0884 | 0.9282 | 0.9524 | 0.04997 | 0.05318 |
| 12 | 2.0945 | 1.0631 | 1.0955 | 0.06519 | 0.07014 |
| 14 | 2.0982 | 1.1949 | 1.2371 | 0.08201 | 0.08931 |

**Table 4.13** Results from AVL for box wing case 12: $h/b = 0{,}62$, decalage $= +9°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.5864 | 0.3287 | 0.3355 | 0.00869 | 0.00868 |
| 2 | 1.8405 | 0.4722 | 0.4825 | 0.01514 | 0.01549 |
| 4 | 1.9555 | 0.6142 | 0.6290 | 0.02382 | 0.02477 |
| 6 | 2.0137 | 0.7545 | 0.7747 | 0.03463 | 0.03649 |
| 8 | 2.0462 | 0.8926 | 0.9195 | 0.04744 | 0.05058 |
| 10 | 2.0656 | 1.0281 | 1.0631 | 0.06208 | 0.06699 |
| 12 | 2.0778 | 1.1607 | 1.2055 | 0.07837 | 0.08563 |
| 14 | 2.0858 | 1.2901 | 1.3464 | 0.09611 | 0.10640 |

**Table 4.14** Results from AVL for box wing case 13: $h/b = 0{,}93$, decalage $= -6°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.6698 | -0.2403 | -0.2371 | 0.00414 | 0.00412 |
| 2 | 0.4719 | -0.0851 | -0.0838 | 0.00118 | 0.00182 |
| 4 | 0.3139 | 0.0699 | 0.0696 | 0.00199 | 0.00189 |
| 6 | 1.4068 | 0.2243 | 0.2230 | 0.00464 | 0.00433 |
| 8 | 1.8985 | 0.3777 | 0.3760 | 0.00968 | 0.00912 |
| 10 | 2.1064 | 0.5295 | 0.5287 | 0.01702 | 0.01624 |
| 12 | 2.2097 | 0.6794 | 0.6806 | 0.02652 | 0.02567 |
| 14 | 2.2682 | 0.8270 | 0.8318 | 0.03803 | 0.03734 |

**Table 4.15** Results from AVL for box wing case 14: $h/b = 0{,}93$, decalage $= -3°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.6695 | -0.1186 | -0.1179 | 0.00102 | 0.00102 |
| 2 | 0.3240 | 0.0354 | 0.0353 | 0.00049 | 0.00047 |
| 4 | 1.8987 | 0.1891 | 0.1885 | 0.00240 | 0.00229 |
| 6 | 2.2068 | 0.3418 | 0.3414 | 0.00668 | 0.00647 |
| 8 | 2.3012 | 0.4933 | 0.4939 | 0.01325 | 0.01298 |
| 10 | 2.3427 | 0.6430 | 0.6458 | 0.02200 | 0.02180 |
| 12 | 2.3652 | 0.7906 | 0.7969 | 0.03279 | 0.03287 |
| 14 | 2.3789 | 0.9356 | 0.9471 | 0.04545 | 0.04616 |

**Table 4.16** Results from AVL for box wing case 15: $h/b = 0{,}93$, decalage $= 0°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 0 | 0.0000 | 0.0000 | 0.00000 | 0.00000 |
| 2 | 2.4268 | 0.1529 | 0.1531 | 0.00119 | 0.00118 |
| 4 | 2.4268 | 0.3051 | 0.3059 | 0.00473 | 0.00472 |
| 6 | 2.4268 | 0.4562 | 0.4584 | 0.01055 | 0.01600 |
| 8 | 2.4268 | 0.6057 | 0.6104 | 0.01856 | 0.01879 |
| 10 | 2.4268 | 0.7533 | 0.7616 | 0.02862 | 0.02926 |
| 12 | 2.4268 | 0.8986 | 0.9118 | 0.04060 | 0.04194 |
| 14 | 2.4268 | 1.0411 | 1.0098 | 0.05430 | 0.05679 |

**Table 4.17** Results from AVL for box wing case 16: $h/b = 0{,}93$, decalage $= +3°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.6689 | 0.1163 | 0.1171 | 0.00101 | 0.00101 |
| 2 | 2.2884 | 0.2680 | 0.2700 | 0.00385 | 0.00390 |
| 4 | 2.3922 | 0.4187 | 0.4226 | 0.00895 | 0.00914 |
| 6 | 2.4212 | 0.5681 | 0.5747 | 0.01623 | 0.01670 |
| 8 | 2.4316 | 0.7157 | 0.7260 | 0.02559 | 0.02654 |
| 10 | 2.4357 | 0.8612 | 0.8765 | 0.03687 | 0.03862 |
| 12 | 2.4374 | 1.0041 | 1.0260 | 0.04994 | 0.05287 |
| 14 | 2.4379 | 1.1442 | 1.1741 | 0.06460 | 0.06923 |

**Table 4.18** Results from AVL for box wing case 17: $h/b = 0{,}93$, decalage $= +6°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.6686 | 0.2310 | 0.2340 | 0.00403 | 0.00402 |
| 2 | 2.1252 | 0.3814 | 0.3868 | 0.00846 | 0.00862 |
| 4 | 2.2887 | 0.5306 | 0.5391 | 0.01506 | 0.01555 |
| 6 | 2.3585 | 0.6782 | 0.6908 | 0.02373 | 0.02477 |
| 8 | 2.3927 | 0.8239 | 0.8416 | 0.03435 | 0.03624 |
| 10 | 2.4111 | 0.9672 | 0.9914 | 0.04678 | 0.04991 |
| 12 | 2.4217 | 1.1078 | 1.1400 | 0.06086 | 0.06570 |
| 14 | 2.4281 | 1.2453 | 1.2872 | 0.07639 | 0.08354 |

**Table 4.19** Results from AVL for box wing case 18: $h/b = 0{,}93$, decalage $= +9°$.

| $\alpha$ (°) | $e_{BW}$ | $C_{L,tot}$ | $C_{L,ff}$ | $C_{D,tot}$ | $C_{D,ff}$ |
|---|---|---|---|---|---|
| 0 | 1.6683 | 0.3447 | 0.3515 | 0.00909 | 0.00906 |
| 2 | 2.0236 | 0.4938 | 0.5041 | 0.01506 | 0.01538 |
| 4 | 2.1971 | 0.6414 | 0.6562 | 0.02310 | 0.02399 |
| 6 | 2.2888 | 0.7872 | 0.8074 | 0.03309 | 0.03487 |
| 8 | 2.3411 | 0.9308 | 0.9577 | 0.04492 | 0.04796 |
| 10 | 2.3729 | 1.0719 | 1.1068 | 0.05842 | 0.06320 |
| 12 | 2.3933 | 1.2101 | 1.2545 | 0.07342 | 0.09050 |
| 14 | 2.4068 | 1.3451 | 1.4007 | 0.08973 | 0.09980 |

In order to be able to compare my results with those of my predecessors, I do similar steps as they did. I am going to build curve $k$ (4.5). First, I look for an average $e$, so that it does not depend on $\alpha$. I start with excluding nonrealistic values -- the one in grey colour. I build function $C_{D,ff}(C_{L,ff}^2)$. It is presented in Figure 4.8. It turns out to be an almost linear function -- $R^2$ is very close to 1. If it was a completely linear function, $e$ would be constant independently from $\alpha$. The difference between two measurements is always 2°. For these reasons, I decide to use simple Equation (4.7) to find $e_A$ -- an average value of Oswald factor. The results are grouped in Table 4.20.

**Figure 4.8** Plot of the function $C_{D,ff}(C_{L,ff}^2)$ for box wing of decalage $+6°$ and $h/b = 0{,}31$. $R^2$ equals almost 1, which means a linear function holds good resemblance to the original one.

$$e_A = \frac{\sum_{i}^{n} e_i}{n} \tag{4.7}$$

$e_i = e_i(\alpha)$ -- Oswald factor for different $\alpha$
$n$ -- number of cases with different $\alpha$ values

**Table 4.20** Average values of Oswald factor for box wing with different $h/b$ ratio and decalage.

| Decalage (°) | | $h/b = 0{,}31$ | | | $h/b = 0{,}62$ | | | $h/b = 0{,}93$ | |
|---|---|---|---|---|---|---|---|---|---|
| | $e_{BW}$ | $e_{BW}/e_{BW,ref}$ | | $e_{BW}$ | $e_{BW}/e_{BW,ref}$ | | $e_{BW}$ | $e_{BW}/e_{BW,ref}$ |
| -6 | 1.5432 | 1.5458 | | 1.8910 | 1.8942 | | 2.1207 | 2.1243 |
| -3 | 1.5862 | 1.5889 | | 2.0240 | 2.0275 | | 2.3190 | 2.3229 |
| 0 | 1.6450 | 1.6478 | | **2.0948** | 2.0984 | | **2.4268** | 2.4309 |
| +3 | **1.6483** | 1.6511 | | 2.0818 | 2.0853 | | 2.3938 | 2.3979 |
| +6 | 1.6314 | 1.6342 | | 1.9287 | 1.9320 | | 2.2913 | 2.2952 |
| +9 | 1.5981 | 1.6008 | | 1.8490 | 1.8522 | | 2.1104 | 2.1139 |

According to (4.4) and (4.5), $k$ depends only on $h/b$. Thus, only one value of $e_A$ may correspond to each $h/b$. Consequently (the same as during research in a wind tunnel), I choose representative $e_A$ associated to the highest $e$. The reason for this is that wings should be compared in their optimum conditions. These values are put in bold font in Table 4.20.

At this point, factors $k_1$, $k_2$, $k_3$ and $k_4$ are to be found. A common method is to set $k_1 = k_3$. This assumption has simple explanation. According to (4.4) $e_{BW} = e_{BW,ref}$ if $k(h/b=0) = 1$. This is true, considering the fact that $h/b = 0$ describes a situation without decalage and that the box wing consists of two identical horizontal wings. $k_2$ and $k_4$ are found by means of Excel Solver.

Table 4.21 contains results from AVL and those collected by other students:
- from iDRAG -- a project by Maarten Waeterschoot
- experiment 1 in Wind Tunnel by Dorendorf
- experiment 2 in Wind Tunnel by Martin Fekete
- also from Hoerner, Prandtl and Rizzo theory gathered by Dorendorf in her project and by Scholz

**Table 4.21** Factors of the function $k(h/b)$ obtained from different sources.

| Method | $k_1$ | $k_2$ | $k_3$ | $k_4$ | Reference |
|--------|--------|--------|--------|--------|-----------|
| AVL (Budziak) | 1.000 | 0.720 | 1.000 | 3.289 | -- |
| iDRAG (Maarten Waeterschoot) | 1.037 | 0.571 | 1.037 | 2.126 | (Waeterschoot, 2012) |
| Wind Tunnel 1 (Dorendorf) | 0.800 | 0.933 | 0.800 | 2.249 | (Scholz, 2015b) |
| Wind Tunnel 2 (Martin Fekete) | 1.220 | 0.630 | 1.220 | 3.740 | (Fekete, 2013) |
| Hoerner | 0.656 | 0.508 | 0.656 | 2.329 | (Scholz, 2015b) |
| Prandtl | 1.000 | 0.450 | 1.040 | 2.810 | (Prandtl, 1924) |
| Rizzo | 0.440 | 0.959 | 0.440 | 2.220 | (Rizzo, 2007) |

Figure 4.9 illustrates plots of $k$ based on $k$ factors from Table 4.21.

**Figure 4.9** Plot of the induced drag factor -- $k$, which is a function of $h/b$ ratio. $k$ is a ratio of span efficiency factor of the box wing over the reference wing. It gives an idea, how much aerodynamically the box wing is better in comparison to (reference) rectangular wing.

The plot derived from AVL is very similar to the one obtained from Prandtl and Hoerner equations and also from experiment 2 in Wind Tunnel, but different from experiment 1. Probably it would be recommended to repeat the experiment to decide which are reliable.

---

## 5 Summary

In the project AVL was used to examine diverse wing configurations: monoplane as well as box wing. Monoplanes differed in aspect ratio and taper ratio, while box wings in $h/b$ ratio. Moreover, they were calculated by means of well-known theoretical formulas. Comparison was based on Oswald factor and induced drag. In the case of monoplanes also on Hoerner function $f(\lambda)$ while in the case of box wings on curve $k$, built already by many research workers and students working in wind tunnel.

It was proved that errors between results from theory and from AVL are insignificantly small. Behaviour of both induced drag and Oswald factor is consistent with reality (or at least theoretical formulas) throughout the range tested. There are some divergence in values. However, the error never exceeded 7.5 %. Generally, AVL gives more optimistic results: higher Oswald factor and lower induced drag. When it comes to box wings, the curve $k$ built on results from AVL bore great resemblance to the ones from Prandtl, Hoerner and Experiment 2 in Wind Tunnel. It differed from Experiment 1.

There was noticeable disagreement in values of Hoerner function $f(\lambda)$. Therefore, first attempt to optimize the function was made. The conclusion is that it depends on $A$ and is only a conservative approximation: it gives a little underestimated value of Oswald factor.

For someone who is familiar with Vortex Lattice Theory, restrictions for application AVL should be obvious. The User Guide from the software website provides necessary information, however, for an inexperienced user it could be a little too brief. It is recommended to go through the Sample Input Files, which can be found there. After some time of studying, program seems to be easy to handle. However, for someone who wants to compare many different geometry models, it may be time-consuming as the process is not automated. On the other hand, once the geometry is created, it is easy to check different flight conditions. An advantage is also a possibility to have a look at the created geometry of the wing and Trefftz Plot.

All in all, AVL seems to be a good choice for someone who wants to assess the potential of his construction and evaluate different possible configurations.

---

## References

**Anderson 2001** -- Anderson, Jr., John D., 2001, *Fundamentals of Aerodynamics*, 3rd Edition, McGraw-Hill, New York, 892 p.

**Baier et al 2013** -- Baier, H., Daoud F., Deinert, S., Petersson, Ö., 2013, *Aircraft Loft Optimization With Respect to Aeroelastic Lift and Induced Drag Loads*, 10th World Congress on Structural and Multidisciplinary Optimization, Orlando, Florida, USA

**Drela and Youngren 2010** -- Drela, M. and Youngren, H., 2010, AVL (3.30) User Primer, *AVL Overview*

**Drela and Youngren 2013** -- Drela, M. and Youngren, H., 2013, *AVL Overview*

**Fekete 2013** -- Fekete, M., 2013, *Induced Drag of Box Wing Aircraft -- Variation of Decalage and Vertical Separation*, Project, Hamburg University of Applied Sciences, Department of Automotive and Aeronautical Engineering

**Gohl 2009** -- Gohl, F., 2009, *Aerodynamic Performance and Stability Simulation of Different Flying Wing Model Airplane Configurations*, Bachelor Thesis, Swiss Federal Institute of Technology in Zurich

**Hoerner 1992** -- Hoerner, S. F., 1992, *Fluid -- Dynamic Drag, Practical Information on Aerodynamic Drag and Hydrodynamic Resistance*, Hoerner Fluid Dynamics, U.S.A.

**Jan 2015** -- Jan, jeklink.net, *CRRCSimAVL Tutorial*

**Katz and Plotkin 1991** -- Katz, J. and Plotkin, A., 1991, *Low-speed Aerodynamics: From Wing Theory to Panel Methods*, McGraw-Hill, Singapore.

**Kroo 2005** -- Kroo, I., 2005, Nonplanar Wing Concepts for Increased Aircraft Efficiency, in: Von Kármán Institute for Fluid Dynamics: VKI Lecture Series: *Innovative Configurations and Advanced Concepts for Future Civil Transport Aircraft*, Von Kármán Institute for Fluid Dynamics, Rhode St-Genèse

**Kroo 2007a** -- Kroo, I., 2007, Trefftz Plane Drag Derivation, *Applied Aerodynamics II, Course Notes Web*, Stanford University

**Kroo 2007b** -- Kroo, I., 2007, Induced Drag and the Trefftz Plane, *Applied Aerodynamics II, Course Notes Web*, Stanford University

**Lavionnaire 2015** -- lavionnaire.fr, *Aérodynamique, La Traînée*

**Liu 2007** -- Liu, C., 2007, *Wake Vortex Encounter Analysis with Different Wake Vortex Models Using Vortex-Lattice Method*, Master of Science Thesis, Delft University of Technology, Faculty of Aerospace Engineering

**Melin 2000** -- Melin, T., 2000, *A Vortex Lattice MATLAB Implementation for Linear Aerodynamic Wing Applications*, Master Thesis, Royal Institute of Technology (KTH), Department of Aeronautics

**Munk 1923** -- Munk, M., 1923, *General Biplane Theory*, National Advisory Committee for Aeronautics

**Nita and Scholz 2012** -- Nita, M., Scholz, D., 2012, *Estimating the Oswald factor from Basic Aircraft Geometrical Parameters*, Hamburg University of Applied Sciences, Aero -- Aircraft Design and Systems Group

**Prandtl 1924** -- Prandtl, L., 1924, *Induced Drag of Multiplane*, National Advisory Committee for Aeronautics, Hampton

**Rizzo 2007** -- Rizzo, E., 2007, *Optimization Methods Applied to the Preliminary Design of Innovative, Non Conventional Aircraft Configuration*, Edizioni ETS, 2007, Pisa

**Schiktanz 2011** -- Schiktanz, D., 2011, *Conceptual Design of a Medium Range Box Wing Aircraft*, Master Thesis, Hamburg University of Applied Sciences, Department of Automotive and Aeronautical Engineering

**Scholz 2015a** -- Scholz, D., 2015, Hamburg University of Applied Sciences, Department of Automotive and Aeronautical Engineering, written communication

**Scholz 2015b** -- Scholz, D., 2015, *Messergebnisseaus der Arbeit von G. Dorendorf weiter verarbeitet*, EXCEL-Table, personal communication

**Waeterschoot 2012** -- Waeterschoot, M., 2012, *The Effect of Variations of the Height to Span Ratio of Box Wing Aircraft on Induced Drag and the Spanwise Lift Distribution*, Project, Hamburg University of Applied Sciences, Department of Automotive and Aeronautical Engineering

---

## Acknowledgements

I would like thank Prof. Dr.-Ing. Dieter Scholz for giving me the opportunity to realise this project with him, for his guidance, knowledge, patience and time that he devoted to me.

I would also like to thank people; both Professors and students, from Hamburg University of Applied Sciences for making me feel welcome at their University.

Special thanks to all the other international students, who became my friends during this Erasmus exchange.

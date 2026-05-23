{ Fill in the following sections (removing comment marks ! if necessary),
  and delete those that are unused.}
TITLE 'Tension1'     { the problem identification }
COORDINATES cartesian2  { coordinate system, 1D,2D,3D, etc }
VARIABLES        { system variables }
  ux !перемещение u_x(x,y)  это искомые функции
  uy !перемещение u_y(x,y) { choose your own names }
SELECT
ngrid=8 
errlim=5e-4         { method controls }
DEFINITIONS
L = 40 !длина
H = 20 !ширина
D = 2  !толщина  { parameter definitions }
k = -3/4
E1 = 200e9 !сталь 
E0 = E1*(exp(k) - 1) / k
E = E1*(exp(k*x))
nu = 0.33 !коэфициент пуассона
sigma0 = 1e-6
exx = dx(ux)
eyy = dy(uy)
exy = 0.5 * (dy(ux) + dx(uy))
ezz = -nu / (1 -nu) * (exx + eyy)
A11 = 1.0
A0 = A11
A12 = 0.8
A16 = 0.2
A22 = 2.0
A26 = 0.1
A66 = 1.0
gamma12 = 2*exy
sxx = A11*exx + A12*eyy + A16*gamma12
syy = A12*exx + A22*eyy + A26*gamma12
sxy = A16*exx + A26*eyy + A66*gamma12				
u1D = (exp(k) - 1) * ( 1 - exp(-k*x)) / k^2
u2D = ux * (E0 / (sigma0*L))
N1  = LINE_INTEGRAL(sxx,'EDGE1')
N2 = LINE_INTEGRAL(sxx,'EDGE2')
R = H / 4
u0 = L / 1000
numP = 16
Px= ARRAY[numP]
Py= ARRAY[numP]
R_points = 4.5
r_corner = 0.25*R   ! Радиус скругления

REPEAT i = 1 BY 1 TO numP/2
    Px[i] = R + R_points * COS(2*Pi*(i-1)/(numP/2))
    Py[i] = R_points * SIN(2*Pi*(i-1)/(numP/2))
ENDREPEAT

REPEAT i = numP/2+1 BY 1 TO numP
    Px[i] = -R + R_points * COS(2*Pi*(i - numP/2 - 1)/(numP/2))
    Py[i] = R_points * SIN(2*Pi*(i - numP/2 - 1)/(numP/2))
ENDREPEAT
EQUATIONS        { PDE's, one for each variable }{ one possibility }
  ux: dx(sxx) + dy(sxy) = 0
  uy: dx(sxy) + dy(syy) = 0 
! CONSTRAINTS    { Integral constraints }
BOUNDARIES       { The domain definition }
  FEATURE 'EDGE1'
  	START (L/2, -H/2)
    LINE TO (L/2,H/2)
  FEATURE 'EDGE2'
  	START(-L/2,-H/2)
    LINE TO (-L/2,H/2)
  REGION 1       { For each material region }
    START(-L/2,-H/2)
    	LOAD(ux) = 0
    	LOAD(uy) = 0{ Walk the domain boundary }
    LINE TO (L/2, -H/2) 
    	VALUE(ux) = u0/2
        VALUE(uy) = 0
    LINE TO (L/2,H/2)
    	LOAD(ux) = 0
    	LOAD(uy) = 0
    LINE TO (-L/2,H/2)
    	VALUE(ux) = -u0/2
    	VALUE(uy) = 0
    LINE TO CLOSE

! ПРАВЫЙ КВАДРАТ
START (0.5*R + r_corner, 0.5*R)
    LOAD(ux) = 0
    LOAD(uy) = 0

LINE TO (1.5*R - r_corner, 0.5*R)
ARC (CENTER = 1.5*R - r_corner, 0.5*R - r_corner) ANGLE = -90

LINE TO (1.5*R, -0.5*R + r_corner)
ARC (CENTER = 1.5*R - r_corner, -0.5*R + r_corner) ANGLE = -90

LINE TO (0.5*R + r_corner, -0.5*R)
ARC (CENTER = 0.5*R + r_corner, -0.5*R + r_corner) ANGLE = -90

LINE TO (0.5*R, 0.5*R - r_corner)
ARC (CENTER = 0.5*R + r_corner, 0.5*R - r_corner) ANGLE = -90 TO CLOSE


! ЛЕВЫЙ КВАДРАТ
START (-1.5*R + r_corner, 0.5*R)
    LOAD(ux) = 0
    LOAD(uy) = 0

LINE TO (-0.5*R - r_corner, 0.5*R)
ARC (CENTER = -0.5*R - r_corner, 0.5*R - r_corner) ANGLE = -90

LINE TO (-0.5*R, -0.5*R + r_corner)
ARC (CENTER = -0.5*R - r_corner, -0.5*R + r_corner) ANGLE = -90

LINE TO (-1.5*R + r_corner, -0.5*R)
ARC (CENTER = -1.5*R + r_corner, -0.5*R + r_corner) ANGLE = -90

LINE TO (-1.5*R, 0.5*R - r_corner)
ARC (CENTER = -1.5*R + r_corner, 0.5*R - r_corner) ANGLE = -90 TO CLOSE
! TIME 0 TO 1    { if time dependent }
MONITORS         { show progress }
PLOTS
 TABLE(exx,eyy,exy) EXPORT
 	format "#x#b#y#b#1#D#2#b#3"
    points = (60,30)
    file = 'strain_tensor.dat'
SUMMARY 
	EXPORT FILE = "summary_output.txt"
    REPORT (L) AS "L"
    REPORT (H) AS "H"
    REPORT (D) AS "D"
    REPORT (R) AS "R"
    REPORT (u0) AS "u0"
    REPORT (N1) AS "N1"
    REPORT (N2) AS "N2"
    REPEAT j = 1 BY 1 TO numP 
    	REPORT (VAL(exx, Px[j], Py[j]), VAL(eyy, Px[j], Py[j]), VAL(exy, Px[j], Py[j])) as 'epsilon' + $j
    endrepeat
    Repeat i = 1 by 1 to numP
    	report(VAL(ux, Px[i], Py[i]) , VAL(uy, Px[i], Py[i]) ) as "u" + $i
    endrepeat
    report (A0, A11/A0, A12/A0, A16/A0, A22/A0, A26/A0, A66/A0) as "A"
    Repeat i = 1by 1 to numP
    	Report(Px[i], Py[i]) AS 'P' + $i
    endrepeat
    Report(numP) AS "number_Points"
 END

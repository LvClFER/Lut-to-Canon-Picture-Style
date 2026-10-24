"""Independent reconstruction of the observed NP3 custom-tone path."""
from bisect import bisect_right
from math import floor
from .grading import round_divide


def custom_tone_curve(record):
    if len(record) != 578 or record[:2] != b'I0':
        raise ValueError('Expected observed NP3 custom tone record')
    if record[2:4] != bytes((0, 255)):
        raise ValueError('Input levels outside observed calibration')
    count = record[8]
    if not 2 <= count <= 27 or record[7] >= 100:
        raise ValueError('Invalid point count or decimal gamma')
    points = list(zip(record[9:9+count*2:2], record[10:10+count*2:2]))
    x, y = zip(*points)
    gamma = record[6] + record[7]/100
    if gamma <= 0 or record[4] > record[5] or any(a >= b for a, b in zip(x, x[1:])):
        raise ValueError('Invalid gamma, output levels or point order')
    h = [b-a for a, b in zip(x, x[1:])]
    slopes = [(b-a)/width for a, b, width in zip(y, y[1:], h)]
    # Natural endpoint conditions; solve the tridiagonal system without NumPy.
    diagonal = [1.0] + [2*(h[i-1]+h[i]) for i in range(1,count-1)] + [1.0]
    rhs = [0.0] + [6*(slopes[i]-slopes[i-1]) for i in range(1,count-1)] + [0.0]
    for i in range(1,count-1):
        factor = h[i-1]/diagonal[i-1]
        diagonal[i] -= factor*(h[i-1] if i > 1 else 0)
        rhs[i] -= factor*rhs[i-1]
    second = [0.0]*count
    for i in range(count-2,0,-1):
        second[i] = (rhs[i]-h[i]*second[i+1])/diagonal[i]
    curve = []
    for sample in range(257):
        query = sample*255/256
        q = min(x[-1], max(x[0], query))
        i = min(count-2, max(0,bisect_right(x,q)-1))
        b = (q-x[i])/h[i]
        a = 1-b
        value = a*y[i]+b*y[i+1]+((a*a*a-a)*second[i]+(b*b*b-b)*second[i+1])*h[i]**2/6
        if x[0] < query < x[-1]:
            position = (query-x[0])/(x[-1]-x[0])
            value += 255*(position**(1/gamma)-position)
        value = record[4]+min(255,max(0,value))*(record[5]-record[4])/255
        curve.append(floor(value*4095/255+0.5))
    return curve


def expand_tone_curve(curve):
    if len(curve) != 257 or any(not isinstance(v,int) or not 0 <= v <= 4095 for v in curve):
        raise ValueError('Expected 257 unsigned 12-bit tone values')
    return [curve[i//16]+round_divide((curve[i//16+1]-curve[i//16])*(i%16),16)
            for i in range(4096)]

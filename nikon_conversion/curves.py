"""Rebuild expanded grid curves from compact knots; no expanded tables read."""
from .grading import round_divide


def expand_curve33(curve):
    if len(curve)!=33 or any(not isinstance(v,int) or not 0<=v<=65535 for v in curve):
        raise ValueError('Expected 33 unsigned16 knots')
    return [(curve[i//128]+round_divide((curve[i//128+1]-curve[i//128])*(i%128),128))%65536
            for i in range(4096)]


def expand_signed_curve65(curve):
    if len(curve)!=65 or any(not isinstance(v,int) or not -32768<=v<=32767 for v in curve):
        raise ValueError('Expected 65 signed16 knots')
    return [(curve[i//64]+round_divide((curve[i//64+1]-curve[i//64])*(i%64),64)+32768)%65536-32768
            for i in range(4096)]

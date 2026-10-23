#include "display_average.h"
#include <cassert>
int main(){
 DisplayAverage a;
 for(unsigned n=0;n<20;++n)a.add(n,2*n,1,0);
 assert(a.count==20 && a.volts==9.5 && a.amps==19);
 a.add(2,3,2,0);assert(a.count==1 && a.volts==2);
 a.add(9,9,2,1);assert(a.count==0);
 a.add(4,5,2,0);a.clear();assert(a.count==0);
}

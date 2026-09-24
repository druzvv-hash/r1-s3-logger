#pragma once
#include <stdint.h>
#include <stdio.h>
// Portable UTC naming/FAT calendar contract, mirrored in the ecosystem modules.
static inline int gll_leap(unsigned y){return y%4==0&&(y%100!=0||y%400==0);}
static inline int gll_calendar(uint64_t us,unsigned *y,unsigned *m,unsigned *d,unsigned *h,unsigned *mi,unsigned *s){
 if(us<946684800000000ULL||us>=4102444800000000ULL)return 0;
 uint64_t sec=us/1000000;unsigned days=(unsigned)(sec/86400);*y=1970;
 while(days>=(unsigned)(gll_leap(*y)?366:365)){days-=gll_leap(*y)?366:365;(*y)++;}
 static const unsigned md[]={31,28,31,30,31,30,31,31,30,31,30,31};*m=1;
 while(days>=md[*m-1]+(*m==2&&gll_leap(*y))){days-=md[*m-1]+(*m==2&&gll_leap(*y));(*m)++;}
 *d=days+1;*h=(unsigned)(sec%86400/3600);*mi=(unsigned)(sec%3600/60);*s=(unsigned)(sec%60);return 1;
}
static inline uint32_t gll_fattime(uint64_t us){unsigned y,m,d,h,mi,s;if(!gll_calendar(us,&y,&m,&d,&h,&mi,&s))return 0;return ((y-1980)<<25)|(m<<21)|(d<<16)|(h<<11)|(mi<<5)|(s/2);}
static inline int gll_session_stem(char *out,size_t n,uint64_t us,uint64_t group,const char *role,const uint8_t device[6]){
 unsigned y,m,d,h,mi,s;char stamp[24];
 if(gll_calendar(us,&y,&m,&d,&h,&mi,&s))snprintf(stamp,sizeof(stamp),"%04u%02u%02uT%02u%02u%02uZ",y,m,d,h,mi,s);
 else snprintf(stamp,sizeof(stamp),"UNKNOWNUTC");
 int len=snprintf(out,n,"%s_G%08lx%08lx_%s_%02x%02x%02x%02x%02x%02x",stamp,(unsigned long)(group>>32),(unsigned long)(group&0xffffffffu),role,device[0],device[1],device[2],device[3],device[4],device[5]);
 return len>0&&(size_t)len<n;
}

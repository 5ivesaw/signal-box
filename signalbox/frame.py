from collections import deque
import hashlib
import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter1d, map_coordinates


def blur(f, sigma):
    return gaussian_filter(f, (sigma,sigma,0), mode='reflect')


def luma(f):
    return f[:,:,0]*.299+f[:,:,1]*.587+f[:,:,2]*.114


class FrameEngine:
    """Bounded source history; one float32 raster traverses selected operations."""
    def __init__(self, effects, width, height, fps, seed=1967):
        self.effects=effects
        self.w,self.h,self.fps,self.seed=width,height,fps,seed
        count=max(2,min(32,int(128*1024**2/(width*height*3))))
        self.history=deque(maxlen=count)
        self.previous=None
        self.first=None
        self.fixed={}
        self.y,self.x=np.mgrid[:height,:width].astype(np.float32)
        self.xn=self.x/max(1,width-1)
        self.yn=self.y/max(1,height-1)

    def sample(self,f, dx=0,dy=0):
        coords=[np.broadcast_to(self.y+dy,(self.h,self.w)),np.broadcast_to(self.x+dx,(self.h,self.w))]
        return np.stack([map_coordinates(f[:,:,c],coords,order=1,mode='reflect') for c in range(3)],axis=2)

    def old(self, n=1):
        return self.history[max(0,len(self.history)-1-n)].astype(np.float32)/255

    def region(self,s):
        x,y,w,h=s.roi
        return np.exp(-(((self.xn-x-w/2)/(w/2))**2+((self.yn-y-h/2)/(h/2))**2)*2)

    def process(self, raw, n, t):
        f=raw.astype(np.float32)/255
        self.history.append(raw.copy())
        if self.first is None:self.first=f.copy()
        for e,s in self.effects:
            if t<s.start or (s.end is not None and t>=s.end) or s.strength==0:continue
            salt=int.from_bytes(hashlib.blake2s(e.id.encode(),digest_size=4).digest(),'little')
            rng=np.random.default_rng((self.seed+salt+n*1009)%(2**63))
            f=self.apply(e.recipe,f,s,n,t,rng)
            f=np.clip(f,0,1).astype(np.float32,copy=False)
        self.previous=f.copy() if any(e.recipe=='feedback' for e,s in self.effects) else None
        return np.round(f*255).astype(np.uint8)

    def apply(self,k,f,s,n,t,rng):
        a=s.strength; h,w=self.h,self.w
        if k in ('stutter','low_fps','time_lapse','akinetopsia','judder','telecine'):
            step=max(2,int(2+10*a))
            if k=='judder':step=3+(int(t*2)%3)
            if k=='telecine':step=2 if n%5<3 else 3
            old=self.old(n%step)
            return .8*old+.2*self.old(min(16,step*2)) if k=='akinetopsia' else old
        if k in ('frame_blend','echo','speed_blend','double_exposure'):
            old=self.old(max(1,int(a*20)))
            if k=='double_exposure':old=np.roll(old,int(w*.03),axis=1)
            mix=(.25+.2*np.sin(t*1.7)) if k=='speed_blend' else a*.7
            return f*(1-mix)+old*mix
        if k in ('interlace','field_order','telecine'):
            out=f.copy(); parity=1 if k=='interlace' else 0
            out[parity::2]=self.old()[parity::2]; return out
        if k=='bob':return f[(np.arange(h)//2*2+n%2).clip(0,h-1)]
        if k in ('freeze','timestamp_jump','loop','reverse','reorder','motion_gaps'):
            if k=='motion_gaps':return self.old() if np.mean(np.abs(f-self.old()))<.012+.06*a else f
            if k=='freeze':
                if t%6<.12:self.fixed['freeze']=f.copy()
                return self.fixed.get('freeze',self.first) if t%6<1+3*a else f
            if k=='timestamp_jump':return self.old(int(20*a)) if t%4>2 else f
            if k=='loop':return self.old(n%max(2,min(len(self.history),int(self.fps*.8)))) if t%4>2 else f
            if k=='reverse':return self.old((n*2)%max(2,len(self.history))) if t%3>2 else f
            return self.old((n%3)*3)
        if k=='slit_scan':
            out=f.copy()
            for i in range(len(self.history)):
                y0=h*i//len(self.history);y1=h*(i+1)//len(self.history)
                out[y0:y1]=self.old(i)[y0:y1]
            return out
        if k=='feedback':return f*(1-a*.8)+np.roll(self.previous if self.previous is not None else f,2,axis=1)*(a*.8)
        if k in ('sensor_noise','film_grain','static','visual_snow','heat_noise','low_light','chroma_noise','fixed_pattern','noise_freeze'):
            if k in ('noise_freeze','fixed_pattern'):
                if k not in self.fixed:
                    fixed_rng=np.random.default_rng(self.seed+71)
                    self.fixed[k]=fixed_rng.normal(0,1,(h,w,1)).astype(np.float32) if k=='noise_freeze' else fixed_rng.normal(0,1,(1,w,1)).astype(np.float32)
                noise=self.fixed[k]
            elif k=='chroma_noise':
                noise=rng.normal(0,1,((h+15)//16,(w+15)//16,3)).astype(np.float32)
                noise=np.repeat(np.repeat(noise,16,0),16,1)[:h,:w]
                return f+blur(noise,4)*a*.13
            else:noise=rng.normal(0,1,(h,w,1)).astype(np.float32)
            amp=.012+a*.09
            if k=='static':amp=.15+a*.5
            if k=='heat_noise':amp*=.2+(t%30)/10
            if k=='film_grain':noise=gaussian_filter(noise,(.55,.55,0));amp*=1.3
            if k in ('visual_snow','sensor_noise','low_light'):noise=noise*(1.2-luma(f)[:,:,None])
            if k=='low_light':f=np.floor(f*(12-6*a))/(12-6*a)
            return f+noise*amp
        if k=='hot_pixels':
            fixed=np.random.default_rng(self.seed+131)
            yy=fixed.integers(0,h,int(8+100*a));xx=fixed.integers(0,w,len(yy))
            f[yy,xx]=np.arange(len(yy))[:,None]%2;return f
        if k in ('aberration','degauss'):
            factor=a*.035*(np.exp(-(t-s.start)/2) if k=='degauss' else 1)
            out=f.copy();out[:,:,0]=self.sample(f,(self.x-w/2)*factor,(self.y-h/2)*factor)[:,:,0]
            out[:,:,2]=self.sample(f,-(self.x-w/2)*factor,-(self.y-h/2)*factor)[:,:,2];return out
        if k in ('bloom','lens_smear','flare','night_vision'):
            lights=np.maximum(f-.65,0)
            if k=='lens_smear':return f+uniform_filter1d(lights,max(3,int(w*.12)),axis=1)*a*4
            if k=='flare':
                small=blur(lights,8); pos=np.unravel_index(np.argmax(luma(small)),(h,w))
                mask=np.exp(-((self.x-pos[1])**2+(self.y-pos[0])**2)/(w*.25)**2)
                return f+mask[:,:,None]*np.mean(lights)*a*5
            if k=='night_vision':
                y=luma(f)+luma(blur(lights,5))*a*3+rng.normal(0,.04*a,(h,w))
                return np.stack([y*.18,y,y*.28],axis=2)
            return f+blur(lights,3+8*a)*a*4
        if k=='autofocus':return blur(f,(.2+3*a)*(1+np.sin(t*1.6)))
        if k=='exposure_pump':return f*(1+a*.4*np.sin(t*2.3))
        if k=='wb_pump':return f*np.array([1+a*.3*np.sin(t),1,1-a*.3*np.sin(t*.9)])
        if k in ('rolling_shutter','stabilization','displacement','metamorphopsia','face_warp','local_scale','emulsion'):
            dx=np.sin(self.yn*10+t*2)*a*w*.025;dy=np.cos(self.xn*9+t)*a*h*.015
            if k=='rolling_shutter':return self.sample(f,dx,0)
            if k=='emulsion':
                dx*=2;dy*=2
                stain=(np.sin(self.xn*17+t*.2)+np.cos(self.yn*21-t*.3)>1)*a*.3
                return self.sample(f,dx,dy)-stain[:,:,None]*np.array([.3,1,.6])
            if k in ('metamorphopsia','face_warp','local_scale'):
                region=self.region(s)
                if k=='local_scale':
                    x,y,rw,rh=s.roi;cx=(x+rw/2)*w;cy=(y+rh/2)*h
                    dx=(self.x-cx)*(.2+.35*np.sin(t))*a;dy=(self.y-cy)*(.2+.35*np.sin(t))*a
                dx*=region;dy*=region
            return self.sample(f,dx,dy)
        if k in ('shake','gate_weave','splice'):
            dx=np.sin(t*3.4)*w*.008*a;dy=np.sin(t*5.9)*h*.008*a
            if k=='gate_weave':dx,dy=rng.normal(0,1,2)*a*2
            if k=='splice':dx=0;dy=(h*.06*a if n%max(1,int(self.fps*4))<2 else 0)
            return self.sample(f,dx,dy)
        if k in ('refresh_bars','pwm','hum_bars'):
            freq=2 if k!='pwm' else 7
            band=.5+.5*np.sin(self.yn*freq*2*np.pi-t*(3 if k=='hum_bars' else 8))
            return f*(1-band[:,:,None]*a*.45)
        if k=='capture_loss':return f*.05 if int(t*10)%47==0 else f
        if k in ('chroma_bleed','chroma_delay','composite','dot_crawl','cross_color'):
            Y=luma(f);I=.596*f[:,:,0]-.274*f[:,:,1]-.322*f[:,:,2];Q=.211*f[:,:,0]-.523*f[:,:,1]+.312*f[:,:,2]
            width=max(3,int(3+a*18))
            if k=='chroma_bleed':I=uniform_filter1d(I,width,axis=1);Q=uniform_filter1d(Q,width*2,axis=1)
            elif k=='chroma_delay':I=np.roll(I,int(a*12+1),axis=1);Q=np.roll(Q,int(a*12+1),axis=1)
            else:
                phase=self.x*np.pi/2+self.y*np.pi+(n%4)*np.pi/2
                carrier=np.cos(phase);quad=np.sin(phase)
                signal=Y+I*carrier+Q*quad
                Iy=uniform_filter1d(signal,5,axis=1)
                Ii=uniform_filter1d(signal*carrier*2,9,axis=1)
                Qq=uniform_filter1d(signal*quad*2,9,axis=1)
                if k in ('composite','dot_crawl'):Y=Y*(1-a)+Iy*a
                if k in ('composite','cross_color'):I=I*(1-a)+Ii*a;Q=Q*(1-a)+Qq*a
            return np.stack([Y+.956*I+.621*Q,Y-.272*I-.647*Q,Y-1.106*I+1.703*Q],axis=2)
        if k in ('tracking','head_switch','head_clog','tape_dropout','tape_chew','horizontal_hold'):
            if k=='tape_chew':return self.sample(f,np.sin(t*1.2)**12*np.sin(self.yn*7)*a*w*.18,0)
            if k=='horizontal_hold':return np.take_along_axis(f,((self.x+np.sin(self.yn*12+t*2)*w*a*.15).astype(int)%w)[:,:,None].repeat(3,axis=2),axis=1)
            out=f.copy()
            if k=='head_switch':y0=int(h*(.93-.05*a));y1=h
            elif k=='tracking':y0=int((.5+.4*np.sin(t*.7))*h);y1=min(h,y0+max(2,int(h*.04)))
            elif k=='head_clog':
                if t%7>2:return f
                y0=int(h*.3);y1=int(h*.5)
            else:
                if rng.random()>.15+a*.4:return f
                y0=int(rng.integers(h));y1=min(h,y0+max(1,int(1+a*4)))
            band=out[y0:y1]
            out[y0:y1]=np.roll(band,int(w*a*.05*np.sin(t*17)),axis=1)*(1-a*.7)+rng.random(band.shape)*a*.7
            return out
        if k=='hold_roll':return np.roll(f,int(t*h*.13*a)%h,axis=0)
        if k=='multipath':return f*(1-a*.3)+np.roll(f,int(w*(.01+a*.05)),axis=1)*a*.3
        if k=='convergence':
            out=f.copy();out[:,:,0]=np.roll(f[:,:,0],int(1+a*6),axis=1);out[:,:,2]=np.roll(f[:,:,2],-int(1+a*6),axis=1);return out
        if k=='retention':return f*(1-a*.25)+self.first*a*.25
        if k=='turn_off':
            phase=(t-s.start)%8
            if phase<5:return f
            sy=max(.002,1-(phase-5));sx=max(.005,1-max(0,phase-6))
            xx=(self.x-w/2)/sx+w/2;yy=(self.y-h/2)/sy+h/2
            mask=(xx>=0)&(xx<w)&(yy>=0)&(yy<h)
            out=self.sample(f,xx-self.x,yy-self.y)*mask[:,:,None]
            return out+np.exp(-((self.x-w/2)**2+(self.y-h/2)**2)/max(1,w*.01)**2)[:,:,None]*max(0,8-phase)
        if k=='power_on':return f+np.exp(-(t-s.start)*12)*a
        if k in ('dust','scratches','disc_rot'):
            out=f.copy()
            if k=='scratches':
                stable=np.random.default_rng(self.seed+int(t/3));xs=stable.integers(0,w,max(1,int(1+4*a)))
                out[:,xs]=out[:,xs]*(1-a)+a*.8
            else:
                count=int((10 if k=='dust' else 60)*a)+1
                yy=rng.integers(0,h,count);xx=rng.integers(0,w,count)
                out[yy,xx]=rng.random((count,3)) if k=='disc_rot' else rng.integers(0,2,(count,1))
            return out
        if k=='light_leak':
            mask=np.exp(-((self.xn-(.05+.08*np.sin(t*.4)))**2)/.025)*(.5+.5*np.sin(t*.7))
            return f+mask[:,:,None]*np.array([1,.25,.03])*a*.8
        if k=='projector_burn':
            radius=max(0,((t-s.start)%10-3)/7)*1.4*a
            d=np.sqrt((self.xn-.5)**2+(self.yn-.5)**2)+.015*np.sin(self.xn*100)*np.cos(self.yn*70)
            edge=np.clip((radius-d)*40,0,1)
            return f*(1-edge[:,:,None])+edge[:,:,None]
        if k=='cue_marks':
            if t%8<.3:
                r=np.sqrt(((self.xn-.91)*w/h)**2+(self.yn-.1)**2)
                f[(r>.022)&(r<.029)]*=1-a
            return f
        if k in ('macroblocks','concealment','vram','missing_texture'):
            out=f.copy();block=max(8,w//32)
            if k=='missing_texture':
                x,y,rw,rh=s.roi;mask=(self.xn>x)&(self.xn<x+rw)&(self.yn>y)&(self.yn<y+rh)
                check=((self.x//16+self.y//16)%2)[:,:,None]*np.array([1,0,1]);out[mask]=check[mask];return out
            for _ in range(int(2+a*20)):
                x=int(rng.integers(0,w));y=int(rng.integers(0,h))
                if k=='concealment':out[y:y+block,x:x+block]=self.old(min(8,len(self.history)-1))[y:y+block,x:x+block]
                else:out[y:y+block,x:x+block]=rng.random(3)
            return out
        if k=='slice_damage':
            y=int((t*.1%1)*h);end=min(h,y+max(1,int(h*.1*a)))
            f[y:end]=np.roll(f[y:end],int(w*.2),axis=1);return f
        if k=='zero_yuv':return np.broadcast_to(np.array([.15,1,.05] if n%2 else [1,0,.8]),f.shape).copy() if n%71<2 else f
        if k=='lost_reference':return f*(1-a*.7)+np.roll(self.old(min(20,len(self.history)-1)),int(t*5)%w,axis=1)*a*.7
        if k=='wrong_stride':
            idx=((self.y*(w+int(a*13))+self.x).astype(int)%(h*w));return f.reshape(-1,3)[idx]
        if k=='wrong_format':return f.reshape(3,h,w).transpose(1,2,0)
        if k=='pixel_sort':
            out=f.copy();lum=luma(f)
            for row in range(h):
                mask=lum[row]>.8-a*.6
                edges=np.flatnonzero(np.diff(np.r_[False,mask,False]))
                for start,end in zip(edges[::2],edges[1::2]):
                    out[row,start:end]=f[row,start:end][np.argsort(lum[row,start:end],kind='stable')]
            return out
        if k=='ordered_dither':
            b=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]])/16-.5
            levels=max(2,int(10-8*a));threshold=np.tile(b,(h//4+1,w//4+1))[:h,:w,None]
            return np.floor(f*levels+threshold)/levels
        if k=='error_dither':
            out=f.copy();levels=max(2,int(8-6*a))
            for y in range(h-1):
                for x in range(1,w-1):
                    old=out[y,x].copy();new=np.round(old*levels)/levels;out[y,x]=new;err=(old-new)/16
                    out[y,x+1]+=err*7;out[y+1,x-1]+=err*3;out[y+1,x]+=err*5;out[y+1,x+1]+=err
            return out
        if k=='thermal':
            y=luma(f);return np.stack([np.clip(y*3,0,1),np.clip(y*3-1,0,1),np.clip(1-abs(y*3-1),0,1)],axis=2)
        if k=='scotoma':
            mask=self.region(s)[:,:,None]*a
            x,y,rw,rh=s.roi;x0=int(x*w);x1=max(x0+1,int((x+rw)*w));y0=int(y*h);y1=max(y0+1,int((y+rh)*h))
            boundary=np.concatenate([f[y0:y0+1,x0:x1].reshape(-1,3),f[max(y0,y1-1):y1,x0:x1].reshape(-1,3)])
            return f*(1-mask)+np.mean(boundary,axis=0)*mask
        if k=='scintillating':
            r=np.sqrt((self.xn-.5)**2+(self.yn-.5)**2);theta=np.arctan2(self.yn-.5,self.xn-.5)
            radius=.1+(t*.025% .5);mask=(abs(r-radius-.012*np.sin(theta*35))<.008)&(theta<2)
            out=blur(f,.4);out[mask]=np.array([.5+.5*np.sin(t*9),.8,.6])*a;return out
        if k=='hemianopia':return f*(1-(1/(1+np.exp(np.clip((self.xn-.5)*40,-50,50))))[:,:,None]*a)
        if k=='floaters':
            mask=np.exp(-((self.yn-.4-.08*np.sin(self.xn*15+t*.2))/.009)**2)*np.exp(-((self.xn-.5-.1*np.sin(t*.3))/.25)**2)
            return f*(1-mask[:,:,None]*a*.4)
        if k=='phosphenes':
            mask=(np.maximum(0,np.sin(self.xn*13+t*.3)*np.cos(self.yn*12-t*.4))**8)[:,:,None]
            return f+mask*np.array([.3,.1,.5])*a
        if k=='curtain':return f*(1-np.clip(((t*.08)%1.3-self.xn)*12,0,1)[:,:,None]*a)
        if k in ('troxler','ganzfeld','tunnel'):
            radius=((self.xn-.5)**2+(self.yn-.5)**2)
            mask=np.clip(radius*4,0,1)[:,:,None]*a*(.5+.5*np.sin(t*.3))
            mean=f.mean(axis=(0,1))
            if k=='ganzfeld':return f*(1-a)+mean*a
            if k=='tunnel':return (f*(1-a*.4)+luma(f)[:,:,None]*a*.4)*(1-mask)
            return f*(1-mask)+mean*mask
        if k=='motion_aftereffect':
            pattern=(.5+.5*np.sin(self.yn*60+(t if t%12<8 else int(t/12)*12+8)*4))[:,:,None]
            return f*(1-a)+pattern*a
        if k=='derealization':
            softened=blur(f,1+a*2);gray=luma(softened)[:,:,None]
            return (softened*(1-a*.7)+gray*a*.7)*.8+.1
        if k=='databend':
            data=(f*255).astype(np.uint8);mask=rng.random((h,w))<a*.003
            data[mask]^=rng.integers(1,255,(int(mask.sum()),3),dtype=np.uint8);return data.astype(np.float32)/255
        raise ValueError(f'Unimplemented frame operation: {k}')

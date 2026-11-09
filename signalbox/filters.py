"""Pure filter builders; all numbers originate from validated project settings."""
def video_filter(key, s, w, h, fps):
    a=s.strength
    loww=max(16,int(w*(.65-.5*a))//2*2)
    lowh=max(16,int(h*(.65-.5*a))//2*2)
    recipes={
      'range_crush': f"lutrgb=r='clip((val-16)*(1+{a}),0,255)':g='clip((val-16)*(1+{a}),0,255)':b='clip((val-16)*(1+{a}),0,255)'",
      'range_wash': f"lutrgb=r='val*{1-.4*a}+{40*a}':g='val*{1-.4*a}+{40*a}':b='val*{1-.4*a}+{40*a}'",
      'matrix_mismatch': 'colormatrix=bt601:bt709',
      'highlight_clip': f'eq=brightness={.12*a}:contrast={1+.7*a}',
      'shadow_crush': f'eq=brightness={-.15*a}:contrast={1+.8*a}',
      'channel_swap': 'colorchannelmixer=rr=0:rb=1:bb=0:br=1',
      'posterize': f"lutrgb=r='floor(val/{int(5+45*a)})*{int(5+45*a)}':g='floor(val/{int(5+45*a)})*{int(5+45*a)}':b='floor(val/{int(5+45*a)})*{int(5+45*a)}'",
      'threshold': f"lutyuv=y='if(gt(val,{int(60+130*a)}),235,16)':u=128:v=128",
      'hue_rotation': f'hue=h={180*a}',
      'invert': 'negate',
      'color_cast': f'colorbalance=rs={.2*a}:gs={-.12*a}:bs={-.2*a}',
      'saturation': f'eq=saturation={1+3*a}',
      'gamma_shift': f'eq=gamma={.4+1.5*a}',
      'polaroid': f'eq=saturation={1-.65*a}:contrast={1-.25*a}:brightness={.05*a},colorbalance=rs={.1*a}:bs={-.12*a}',
      'pixelate': f'scale={loww}:{lowh}:flags=neighbor,scale={w}:{h}:flags=neighbor',
      'aliasing': f'scale={loww}:{lowh}:flags=neighbor,scale={w}:{h}:flags=lanczos',
      'soft_upscale': f'scale={loww}:{lowh}:flags=bilinear,scale={w}:{h}:flags=bilinear',
      'digital_zoom': f'crop=iw*{.85-.45*a}:ih*{.85-.45*a},scale={w}:{h}:flags=neighbor',
      'aspect_stretch': f'crop=iw*{.9-.4*a}:ih,scale={w}:{h}',
      'hard_crop': f'crop=iw*{.97-.2*a}:ih*{.97-.2*a},scale={w}:{h}',
      'sharpen': f'unsharp=5:5:{.5+2*a}:5:5:{a}',
      'nr_smear': f'hqdn3d={2+10*a}:{2+8*a}:{4+12*a}:{4+12*a}',
      'fisheye': f'lenscorrection=k1={-.08-.4*a}:k2={-.08*a}',
      'vignette': f'vignette=angle={.25+.8*a}',
      'optical_flow': f'fps={max(3,round(fps*(.5-.3*a)))},tpad=stop_mode=clone:stop_duration=2,minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
    }
    return recipes[key]


def audio_filter(key, s):
    a=s.strength
    recipes={
      'lowpass':f'lowpass=f={12000-10500*a}',
      'spectral_hole':f'equalizer=f=1800:t=q:w=.7:g={-10-35*a}',
      'phone':'highpass=f=300,lowpass=f=3400',
      'radio':f'highpass=f=450,lowpass=f=2700,acompressor=threshold=.12:ratio=6,asoftclip=type=tanh:threshold={.8-.5*a}',
      'tv_speaker':f'highpass=f=350,lowpass=f=5500,equalizer=f=1800:t=q:w=1:g={4+8*a}',
      'mic_overload':f'volume={1+6*a},asoftclip=type=tanh:threshold=.7',
      'clip':f'volume={1+8*a},asoftclip=type=hard:threshold=.8',
      'bitcrush':f'acrusher=bits={max(2,12-10*a)}:mix=1:mode=lin',
      'sample_reduce':f'acrusher=samples={2+20*a}:mix=1',
      'resample':f'aresample={int(16000-10000*a)}:filter_size=2,aresample=48000:filter_size=2',
      'pitch':f'asetrate={int(48000*(.7+.6*a))},aresample=48000',
      'phase':f'pan=stereo|c0=c0-{.3+.6*a}*c1|c1=c1-{.3+.6*a}*c0',
      'channel_drop':'pan=stereo|c0=c0|c1=0*c1',
      'compressor':f'acompressor=threshold={.25-.2*a}:ratio={2+16*a}:attack=5:release=250:makeup=2',
      'gate':f'agate=threshold={.015+.15*a}:ratio=10:attack=2:release=30',
      'noise_suppression':f'afftdn=nr={15+70*a}:nf=-25',
      'reverb':f'aecho=.8:.7:60|127|239:{.15+.3*a}|{.1+.25*a}|{.08+.2*a}',
      'tape_saturation':f'volume={1+3*a},asoftclip=type=tanh:threshold=.8,lowpass=f={15000-8000*a}',
      'formant':f'rubberband=pitch={.7+.6*a}:formant=shifted',
      'dead_room':f'agate=threshold={.01+.08*a}:ratio=20:release=50',
      'answering':'highpass=f=350,lowpass=f=2900,acrusher=bits=8,asoftclip=type=tanh',
    }
    return recipes[key]

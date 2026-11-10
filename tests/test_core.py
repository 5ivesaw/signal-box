import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
from signalbox.catalog import CATALOG,BY_ID
from signalbox.model import Project,Setting
from signalbox.frame import FrameEngine
from signalbox.audio import synth,process_audio,RATE
from signalbox.analysis import chaos,select_all,apply_auto,recommend

class CapabilityTests(unittest.TestCase):
    def test_old_and_new_ffmpeg_filter_listings(self):
        from signalbox.media import parse_capability_table
        old=' TSC highpass A->A Apply highpass\n ... fps V->V Force fps\n T.. = Timeline'
        new=' TS highpass A->A Apply highpass\n .. fps V->V Force fps\n T.. = Timeline'
        self.assertEqual(parse_capability_table(old,'filters'),{'highpass','fps'})
        self.assertEqual(parse_capability_table(new,'filters'),{'highpass','fps'})
        self.assertEqual(parse_capability_table(' V..... = Video\n V....D libx264 encoder','encoders'),{'libx264'})

class ModelTests(unittest.TestCase):
    def test_roundtrip_and_unknown_version(self):
        p=Project(source='source.mp4');p.set('wow');p.effects['wow'].locked=True
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'project.json';p.save(dest);restored=Project.load(dest)
            self.assertEqual(restored.effects,p.effects)
            self.assertEqual(restored.source,str(Path(tmp)/'source.mp4'))
        with self.assertRaises(ValueError):Project.from_dict({'schema':99})
        with self.assertRaises(ValueError):Project.from_dict({'effects':{'imaginary':{}}})
        with self.assertRaises(ValueError):Project.from_dict({'effects':{'wow':{'strength':float('nan')}}})

    def test_project_save_protects_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.json';source.write_text('source bytes')
            p=Project(source=str(source))
            with self.assertRaises(ValueError):p.save(source)
            self.assertEqual(source.read_text(),'source bytes')
            with self.assertRaises(ValueError):p.save(Path(tmp)/'wrong.mp4')

    def test_modes_and_locks(self):
        p=Project();p.effects['hiss']=Setting(enabled=False,locked=True)
        p.effects['tracking']=Setting(enabled=True,locked=True)
        first=chaos(copy.deepcopy(p),seed=47);second=chaos(copy.deepcopy(p),seed=47)
        self.assertEqual(first.to_dict(),second.to_dict())
        self.assertFalse(first.effects['hiss'].enabled);self.assertTrue(first.effects['tracking'].enabled)
        apply_auto(first,{'recommendations':[{'id':'hiss','strength':.5}]})
        self.assertFalse(first.effects['hiss'].enabled);self.assertTrue(first.effects['tracking'].enabled)
        select_all(first);self.assertEqual(len(first.enabled()),len(CATALOG))

    def test_analysis_adapts(self):
        base={'metrics':dict(luma=.5,contrast=.2,detail=.03,saturation=.1,noise_proxy=.01,motion=.01,
             flicker=.01,clipped_fraction=.01,dark_fraction=.01,bright_fraction=.01),
             'duration':60,'audio':{'present':False}}
        night=copy.deepcopy(base);night['metrics'].update(dark_fraction=.9,detail=.1,motion=.2,saturation=.6)
        self.assertNotEqual(recommend(base),recommend(night))
        self.assertTrue(all(r['reason'] for r in recommend(night)))

class FrameTests(unittest.TestCase):
    def test_every_frame_operation(self):
        rng=np.random.default_rng(100);frame=rng.integers(0,256,(48,64,3),np.uint8)
        for e in CATALOG:
            if e.kind!='frame' and e.recipe!='databend':continue
            with self.subTest(effect=e.id):
                engine=FrameEngine([(e,Setting())],64,48,12,seed=7)
                for n,t in [(0,0),(1,.1),(5,3.2),(9,6.7)]:
                    result=engine.process(frame,n,t)
                    self.assertEqual(result.shape,frame.shape);self.assertEqual(result.dtype,np.uint8)

    def test_strength_zero_and_window(self):
        f=np.random.default_rng(3).integers(0,256,(48,64,3),np.uint8)
        for setting in [Setting(strength=0),Setting(start=2,end=3)]:
            engine=FrameEngine([(BY_ID['static'],setting)],64,48,12)
            np.testing.assert_array_equal(engine.process(f,0,0),f)

    def test_temporal_history_and_reproducibility(self):
        black=np.zeros((48,64,3),np.uint8);white=np.full_like(black,255)
        engine=FrameEngine([(BY_ID['interlace'],Setting())],64,48,12)
        engine.process(black,0,0);out=engine.process(white,1,.1)
        self.assertTrue((out[::2]==255).all());self.assertTrue((out[1::2]==0).all())
        a=FrameEngine([(BY_ID['sensor_noise'],Setting())],64,48,12,41)
        b=FrameEngine([(BY_ID['sensor_noise'],Setting())],64,48,12,41)
        np.testing.assert_array_equal(a.process(black,0,0),b.process(black,0,0))
        for n in range(70):engine.process(white,n,n/12)
        self.assertLessEqual(len(engine.history),32)

class AudioTests(unittest.TestCase):
    def test_every_audio_operation(self):
        t=np.arange(RATE*2)/RATE
        data=np.stack([.2*np.sin(t*440*2*np.pi),.2*np.sin(t*660*2*np.pi)],axis=1).astype(np.float32)
        for e in CATALOG:
            if e.kind!='audio':continue
            with self.subTest(effect=e.id):
                result=synth(e.recipe,data,np.arange(5000,9000),Setting(),42)
                self.assertEqual(result.shape,(4000,2));self.assertTrue(np.isfinite(result).all())

    def test_print_through_is_forward_pre_echo(self):
        data=np.zeros((RATE*2,2),np.float32);data[RATE]=1
        idx=np.arange(RATE*2)
        out=synth('print_through',data,idx,Setting(strength=1),17)
        self.assertAlmostEqual(float(out[RATE-int(.7*RATE),0]),.2,places=5)
        self.assertEqual(out[RATE,0],1)
        self.assertEqual(out[RATE+int(.7*RATE),0],0)

    def test_disk_backed_reverse(self):
        from signalbox.media import Job
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.f32';out=Path(d)/'result.f32'
            data=np.arange(200,dtype=np.float32).reshape(100,2)/200;data.tofile(path)
            process_audio(path,out,[(BY_ID['audio_reverse'],Setting())],Job())
            np.testing.assert_array_equal(np.fromfile(out,'<f4').reshape(-1,2),data[::-1])

if __name__=='__main__':unittest.main()

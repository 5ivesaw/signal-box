import json
import unittest
import numpy as np
from signalbox import browser
from signalbox.model import Project,Setting
from signalbox.catalog import BY_ID
from signalbox.frame import FrameEngine
from signalbox.audio import synth,RATE

class BrowserBridgeTests(unittest.TestCase):
    def setup_project(self,ids):
        p=Project(source='local.mp4',width=64,fps=12)
        for key in ids:p.set(key)
        browser.configure(json.dumps(p.to_dict()),json.dumps({'width':64,'height':48,'fps':12}))
        return p

    def test_shared_picture_math_and_chunk_history(self):
        p=self.setup_project(['composite','interlace','echo'])
        raw=np.random.default_rng(12).integers(0,256,(6,48,64,3),dtype=np.uint8)
        expected=FrameEngine([(BY_ID[k],p.effects[k]) for k in ['interlace','echo','composite']],64,48,12,p.seed)
        gold=np.stack([expected.process(f,n,n/12) for n,f in enumerate(raw)])
        first=browser.process_frames(raw[:3].tobytes(),json.dumps({'start':0}))
        second=browser.process_frames(raw[3:].tobytes(),json.dumps({'start':3/12}))
        np.testing.assert_array_equal(np.frombuffer(first+second,np.uint8).reshape(raw.shape),gold)

    def test_chroma_noise_nonmultiple_raster(self):
        p=Project(source='local.mp4');p.set('chroma_noise')
        browser.configure(json.dumps(p.to_dict()),json.dumps({'width':96,'height':54,'fps':12}))
        raw=np.zeros((2,54,96,3),np.uint8)
        result=browser.process_frames(raw.tobytes(),json.dumps({'start':0}))
        self.assertEqual(len(result),raw.nbytes)
        self.assertGreater(np.frombuffer(result,np.uint8).max(),0)

    def test_shared_audio_math(self):
        p=self.setup_project(['wow'])
        t=np.arange(RATE)/RATE;raw=np.stack([np.sin(t*440)*.1,np.sin(t*330)*.1],axis=1).astype('<f4')
        browser.begin_audio(raw.tobytes());browser.audio_effect('wow');out=np.frombuffer(browser.finish_audio(),'<f4').reshape(-1,2)
        gold=synth('wow',raw,np.arange(len(raw)),p.effects['wow'],1)
        np.testing.assert_allclose(out,gold,atol=1e-6)

    def test_asset_window(self):
        p=self.setup_project(['intrusion']);p.effects['intrusion'].start=.25;p.effects['intrusion'].end=.5
        browser.configure(json.dumps(p.to_dict()),json.dumps({'width':64,'height':48,'fps':12}))
        black=np.zeros((12,48,64,3),np.uint8);white=np.full_like(black,255)
        out=np.frombuffer(browser.composite_asset(black.tobytes(),white.tobytes(),json.dumps({'id':'intrusion','start':0,'asset_origin':.25})),np.uint8).reshape(black.shape)
        self.assertEqual(out[:3].max(),0);self.assertEqual(out[3:6].min(),255);self.assertEqual(out[6:].max(),0)

    def test_incremental_analysis(self):
        browser.analysis_begin(json.dumps({'duration':2,'width':160,'height':96,'fps':12,'audio':False}))
        raw=np.random.default_rng(1).integers(0,256,(24,96,160,3),np.uint8)
        browser.analysis_frames(raw[:12].tobytes(),0);browser.analysis_frames(raw[12:].tobytes(),1)
        report=json.loads(browser.analysis_finish());self.assertEqual(report['frames_examined'],24);self.assertTrue(report['recommendations'])

if __name__=='__main__':unittest.main()

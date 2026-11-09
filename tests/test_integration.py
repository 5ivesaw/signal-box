import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from signalbox.model import Project,Setting
from signalbox.catalog import CATALOG,BY_ID
from signalbox.media import Job,Cancelled,probe,ffmpeg,capabilities
from signalbox.render import render,preview,preflight
from signalbox.analysis import analyze

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.source=cls.root/'source with spaces.mp4'
        subprocess.run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=128x96:rate=12:duration=3',
          '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=3',
          '-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(cls.source)],check=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def project(self):return Project(source=str(self.source),width=128,fps=12)

    def test_analysis_entire_video(self):
        report=analyze(self.source)
        self.assertEqual(report['frames_examined'],36)
        self.assertGreaterEqual(report['audio']['samples'],47000)
        self.assertTrue(report['recommendations'])

    def test_render_codec_audio_and_preview(self):
        p=self.project()
        for key in ('composite','tracking','wow','print_through','compression','phone'):p.set(key)
        path=self.root/'stack.mp4';manifest=render(p,path,overwrite=True)
        meta=probe(path);self.assertTrue(meta['audio']);self.assertEqual(meta['width'],128)
        self.assertAlmostEqual(meta['duration'],3,delta=.15)
        subprocess.run(ffmpeg()+['-i',str(path),'-f','null','-'],check=True)
        self.assertEqual(manifest['project']['seed'],p.seed)
        with self.assertRaises(FileExistsError):render(p,path)
        with self.assertRaises(ValueError):render(p,self.source,overwrite=True)
        cached=preview(p,self.root/'cache',effect_id='echo',duration=1)
        stat=cached.stat().st_mtime_ns
        self.assertEqual(preview(p,self.root/'cache',effect_id='echo',duration=1),cached)
        self.assertEqual(cached.stat().st_mtime_ns,stat)

    def test_assets_and_missing_assets(self):
        p=self.project();p.set('intrusion');p.set('crosstalk')
        self.assertEqual(len(preflight(p)['errors']),2)
        p.effects['intrusion'].asset=str(self.source);p.effects['intrusion'].start=.5;p.effects['intrusion'].end=1.5
        p.effects['crosstalk'].asset=str(self.source)
        render(p,self.root/'assets.mp4',duration=2,overwrite=True)
        self.assertTrue(probe(self.root/'assets.mp4')['audio'])

    def test_cancel_does_not_publish(self):
        p=self.project();path=self.root/'cancelled.mp4';job=Job();job.cancel()
        with self.assertRaises(Cancelled):render(p,path,job=job)
        self.assertFalse(path.exists());self.assertFalse(list(self.root.glob('.signalbox-*')))

    def test_filters_available_and_parse(self):
        from signalbox.filters import video_filter,audio_filter
        caps=capabilities()
        for e in CATALOG:
            if e.kind not in ('vf','af') or e.recipe=='audio_reverse':continue
            with self.subTest(effect=e.id):
                p=self.project();p.set(e.id)
                if preflight(p)['errors']:continue
                args=ffmpeg()+['-i',str(self.source),'-t','0.3']
                if e.kind=='vf':args+=['-an','-vf',video_filter(e.recipe,Setting(),128,96,12)]
                else:args+=['-vn','-af',audio_filter(e.recipe,Setting())]
                result=subprocess.run(args+['-f','null','-'],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_optical_flow_preserves_selected_duration(self):
        p=self.project();p.set('optical_flow')
        out=self.root/'flow.mp4';render(p,out,duration=1,overwrite=True)
        self.assertAlmostEqual(probe(out)['duration'],1,delta=.09)

    def test_preview_interval_and_strength_zero(self):
        p=self.project();p.set('invert');p.effects['invert'].strength=0
        out=self.root/'interval.mp4';render(p,out,start=1,duration=1,overwrite=True)
        self.assertAlmostEqual(probe(out)['duration'],1,delta=.09)
        p.effects['invert'].start=.5
        # A zero-strength stage is bypassed entirely; an active invalid window fails.
        p.effects['invert'].strength=.5
        self.assertTrue(preflight(p)['errors'])

    def test_no_audio_source_and_synthetic_bed(self):
        silent=self.root/'silent.mkv';subprocess.run(ffmpeg()+['-i',str(self.source),'-an','-c:v','copy',str(silent)],check=True)
        p=self.project();p.source=str(silent);p.set('hum')
        out=self.root/'bed.mp4';render(p,out,duration=1,overwrite=True)
        self.assertTrue(probe(out)['audio'])

if __name__=='__main__':unittest.main()

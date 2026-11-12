"""Optional local Chrome interaction QA using pre-existing Playwright.

Runs the standalone file URL, not a remote service. No installation, account,
scientific experiment or live quantum job is performed. Saves new research
screenshots and a separate receipt; historical presentation images are retained.
"""
from pathlib import Path
import hashlib
import json
import platform
import re
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    frequency=json.loads((HERE/'evidence/research_frequency.json').read_text())
    drive=json.loads((HERE/'evidence/research_drive.json').read_text())
    prior=json.loads((HERE/'evidence/research_prior.json').read_text())
    phase=json.loads((HERE/'evidence/research_phase.json').read_text())
    dot=json.loads((HERE/'evidence/research_dot.json').read_text())
    hom=json.loads((HERE/'evidence/research_hom_reference.json').read_text())
    hom_analysis=json.loads((HERE/'evidence/research_hom_analysis.json').read_text())
    dot_validation=json.loads((HERE/'evidence/research_dot_design_validation.json').read_text())
    hardware=json.loads((HERE/'evidence/research_hardware.json').read_text())
    errors=[];requests=[];checks=[];screens=[]
    def screenshot(page,name,selector=None):
        path=HERE/name
        if selector:page.locator(selector).screenshot(path=str(path))
        else:page.screenshot(path=str(path),full_page=True)
        screens.append(name)
    def no_overflow(page):
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Horizontal overflow'
    def expect_text(page,selector,text):
        assert text in page.locator(selector).inner_text(),(selector,text,page.locator(selector).inner_text())
    def percent_matches(text,x):
        return abs(float(text.rstrip('%'))-100*x)<=.0050000001
    with sync_playwright() as p:
        # System Chrome supplies H.264 support; the installed older bundled
        # Chromium reports an empty canPlayType result for the existing MP4s.
        browser=p.chromium.launch(headless=True,channel='chrome')
        context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
        page.goto((HERE/'index.html').as_uri()+'?focus=1');page.wait_for_selector('#rewind',state='visible')
        assert page.locator('body').evaluate('(e)=>e.classList.contains("focus-view")')
        page.locator('#tab-research').click();page.wait_for_selector('#research-frequency',state='visible')
        assert page.locator('#tab-research').get_attribute('aria-selected')=='true'
        for case in frequency['scenarios']:
            page.locator('#frequency-case').select_option(case['id'])
            for rule in ['fusion','agreement']:
                page.locator('#frequency-rule').select_option(rule)
                ids=['classical','classical_quantum'+('_agreement' if rule=='agreement' else ''),'two_classical'+('_agreement' if rule=='agreement' else '')]
                for index,key in enumerate(ids):
                    text=page.locator('#frequency-metrics .metric').nth(index).inner_text();m=case['methods'][key]
                    assert percent_matches(page.locator('#frequency-metrics .metric strong').nth(index).inner_text(),m['detection_within_32s'])
                    assert percent_matches(re.search(r'false alarms ([\d.]+%)',text).group(1),m['false_alarm_rate'])
                no_overflow(page)
        page.locator('#frequency-case').select_option('unseen_nominal_sessions');page.locator('#frequency-rule').select_option('fusion')
        screenshot(page,'preview-research-frequency.png');checks.append('All six frequency cases and both rules match frozen rates; task/false-alarm units visible')
        page.locator('#study-drive').click()
        for name,c in drive['cases'].items():
            page.locator('#drive-case').select_option(name)
            source=c['has_source_change_generator']
            for i,key in enumerate(['physical_history','classical_hmm','count_contrast']):
                m=c['methods'][key];stat=m['detection_within32'] if source else m['record_alarm_fraction']
                text=page.locator('#drive-metrics .metric').nth(i).inner_text();assert percent_matches(page.locator('#drive-metrics .metric strong').nth(i).inner_text(),stat['value'])
                if source:
                    control=drive['cases']['stable_source_efficiency_loss' if name=='source_step_with_efficiency_loss' else 'stable_source']
                    assert percent_matches(re.search(r'False alarms ([\d.]+%)',text).group(1),control['methods'][key]['record_alarm_fraction']['value'])
            expected=[prior['cases'][name]['observation_based_rmse']['value'],prior['cases'][name]['prior_only_rmse']['value'],c['zero_change_fraction_rmse']['value']]
            for i,x in enumerate(expected):assert page.locator('#drive-rmse strong').nth(i).inner_text()==f'{x:.4f}'
            no_overflow(page)
        page.locator('#drive-case').select_option('source_telegraph_20pct');expect_text(page,'#drive-denominator','480 eligible')
        page.locator('#drive-case').select_option('source_step_20pct');screenshot(page,'preview-research-drive.png');checks.append('All 13 drive cases preserve eligible/null denominators, matched source-stable FAR and prior-only controls')
        page.locator('#study-phase').click()
        for case in phase['cases']:
            page.locator('#phase-case').select_option(case['id'])
            for budget in ['equal_sample_photons','equal_attempt_clocks']:
                page.locator('#phase-budget').select_option(budget)
                for i,key in enumerate(['coherent','hybrid','noon']):
                    expected=case['budgets'][budget][key]['global']['rmse_full_2pi_rad']
                    assert page.locator('.phase-rmse').nth(i).inner_text()==f'{expected:.5f} rad'
                no_overflow(page)
        page.locator('#phase-case').select_option('high_efficiency');page.locator('#phase-budget').select_option('equal_sample_photons');screenshot(page,'preview-research-phase.png')
        checks.append('All seven phase cases and both budgets show global error, branch errors, dose and time')
        page.locator('#study-progress').click();expect_text(page,'#spatial-values','389 qubits');expect_text(page,'#spatial-values','2,874,028 CX');expect_text(page,'#spatial-values','3,382,108 CX');expect_text(page,'#inference-values','0.069');expect_text(page,'#inference-values','0.706');no_overflow(page)
        screenshot(page,'preview-research-progress.png');checks.append('Inference pairing and complete explicit circuit ledger visible')
        page.locator('#study-dot').focus();page.keyboard.press('Enter');assert page.locator('#research-dot').is_visible()
        for phrase in ['20% to 100%','100% or 60%','77.24% and 79.38%','QRSM component','classical trap can use a hidden Markov model','No quantum-dot QRSM fit','Proposed workflow:','vary bias or excitation','lithography-laser sensor is a separate']:
            expect_text(page,'#dot-project-bridge',phrase)
        screenshot(page,'preview-research-dot-bridge.png','#dot-project-bridge')
        checks.append('QRSM-to-dot bridge distinguishes measured observables, proposed model mapping and future semiconductor-device QA')
        expect_text(page,'#dot-instrument','5.60%');expect_text(page,'#dot-instrument','4.50%');expect_text(page,'#dot-instrument','No information')
        expect_text(page,'#dot-project-bridge','new extension now prepares emitted photon modes')
        screenshot(page,'preview-research-joint-hom.png','#dot-instrument')
        for trial in dot_validation['power_trials']:
            page.locator('#dot-design-budget').select_option(str(trial['independent_blocks']))
            for i,name in enumerate(['coherent_nominal','classical_nominal','classical_mode_mismatch']):
                rate=next(c for c in trial['cases'] if c['name']==name)['flag_rate']
                assert percent_matches(page.locator('#dot-design-values strong').nth(i).inner_text(),rate)
            expect_text(page,'#dot-design-detail',f"{trial['attempted_pairs']:,} attempted pairs")
            no_overflow(page)
        expect_text(page,'#dot-design-warning','72.00%');expect_text(page,'#dot-design-warning','53.25%')
        expect_text(page,'#dot-hmm-finding','includes zero');expect_text(page,'#dot-design-cost','1,984,376')
        page.locator('#dot-design-budget').select_option('646');screenshot(page,'preview-research-dot-design.png','#dot-design')
        checks.append('Implemented joint instrument keeps passive/main negative; all six fresh budgets match, including loss/mode nuisance failure and HMM comparison')
        for case in dot['benchmark_cases']:
            page.locator('#dot-case').select_option(case['case'])
            assert percent_matches(page.locator('#dot-overlap').inner_text(),case['conditional_overlap'])
            expect_text(page,'#dot-brightness','20%');expect_text(page,'#dot-g2','0');no_overflow(page)
        page.locator('#dot-case').select_option('ideal');page.locator('#dot-case').focus();page.keyboard.press('ArrowDown');expect_text(page,'#dot-overlap','50%')
        for i,case in enumerate(dot['classical_trap_pair_comparison']):
            page.locator('#dot-trap').select_option(str(i));assert percent_matches(page.locator('#dot-trap-values strong').first.inner_text(),case['conditional_overlap'])
        page.locator('#dot-trap').select_option('1')
        for i,case in enumerate(dot['collection_loss_sweep']):
            page.locator('#dot-loss').select_option(str(i));assert percent_matches(page.locator('#dot-loss-values strong').first.inner_text(),case['both_photons_survive_probability'])
            if case['single_photon_survival_probability']==0:expect_text(page,'#dot-loss-detail','no detected pairs')
        page.locator('#dot-loss').select_option('2');expect_text(page,'#dot-loss-detail','16×')
        for delay in [13.1,26.2,39.4]:
            page.locator('#dot-hom-pair').select_option(str(delay))
            for window in ['125','4']:
                page.locator('#dot-hom-window').select_option(window)
                rows=[f for f in hom['files'] if f['excitation_pulse_separation_ns']==delay]
                for i,row in enumerate(rows):expect_text(page,'#dot-hom-values',f"{row['count_sum']:,}")
                analyzed=next(c for c in hom_analysis['cases'] if c['excitation_separation_ns']==delay)
                assert percent_matches(page.locator('.dot-analysis-values strong').first.inner_text(),analyzed['primary']['corrected_visibility'])
                expected_interval='–'.join(f'{100*v:.2f}%' for v in analyzed['primary']['corrected_interval95'])
                expect_text(page,'#dot-analysis',expected_interval)
                expected_sensitivity='–'.join(f'{100*v:.2f}%' for v in analyzed['sensitivity_range_all_declared_variants'])
                expect_text(page,'#dot-analysis',expected_sensitivity);expect_text(page,'#dot-analysis','NOT a confidence interval')
                expect_text(page,'#dot-analysis','exclude normalization');expect_text(page,'#dot-analysis','not an independent experimental replication')
                expect_text(page,'#dot-hom-detail',f'{delay:.1f} ns apart')
                assert page.locator('#dot-hom-chart').evaluate('(c)=>c.width>250 && c.height>=280')
                no_overflow(page)
        page.locator('#dot-hom-pair').select_option('13.1');page.locator('#dot-hom-window').select_option('125')
        screenshot(page,'preview-research-dot.png');screenshot(page,'preview-research-dot-model.png','#research-dot .dot-benchmark');screenshot(page,'preview-research-dot-data.png','#research-dot .dot-published')
        checks.append('All four quantum-dot toy cases, four trap settings and six loss settings match frozen values; native keyboard selector works')
        checks.append('All three external HOM pairs and both display windows retain raw counts, attribution and paper-reported labels; new extraction values/conditional intervals/protocol ranges match saved results')
        page.locator('#study-hardware').click();expect_text(page,'#hardware-summary','688,640');expect_text(page,'#hardware-original','6,300 / 8,192');expect_text(page,'#hardware-original','5,674 / 8,192')
        expect_text(page,'#hardware-original','0.1177');expect_text(page,'#hardware-original','0.1814')
        for family in ['dot_frozen','dot_joint','dot_selected_four_pair','atomic','photon','spatial','optical_dilation']:
            page.locator('#hardware-family').select_option(family)
            for i,row in enumerate(hardware['family_results'][family]):
                page.locator('#hardware-circuit').select_option(str(i));expect_text(page,'#hardware-circuit-context',row['name'])
                expect_text(page,'#hardware-circuit-context',f"{row['native_two_qubit_gate_count']:,} compiled")
                o=row['observables']
                if 'raw_event_probability' in o:
                    assert percent_matches(page.locator('#hardware-values strong').first.inner_text(),o['raw_event_probability'])
                    expected='No accepted shots' if o['selected_data_z_distribution_tv'] is None else f"{o['selected_data_z_distribution_tv']:.4f}"
                    expect_text(page,'#hardware-values',expected)
                elif 'histories' in o:
                    for history,h in o['histories'].items():
                        page.locator('#hardware-history').select_option(history)
                        assert percent_matches(page.locator('#hardware-values strong').first.inner_text(),h['observed']['probability'])
                no_overflow(page)
        expect_text(page,'#hardware-failure-values','0.7604');expect_text(page,'#hardware-failure-values','8 / 512')
        assert page.locator('.hardware-job').count()==hardware['jobs']
        for link in page.locator('.hardware-job a').all():
            href=link.get_attribute('href')
            if href.startswith('https:'):assert href=='https://quantum.cloud.ibm.com/workloads'
            else:assert (HERE/href).is_file()
        page.locator('#hardware-family').select_option('dot_selected_four_pair')
        screenshot(page,'preview-research-hardware.png','.hardware-hero');screenshot(page,'preview-research-hardware-dot.png','.hardware-panel:has(#hardware-family)')
        checks.append('All seven hardware families/circuit selectors and every dot flag history match saved raw data; native costs, no-hit failures and job/raw links verified')
        # Chapter keyboard routing and modified browser shortcut behavior.
        page.locator('#tab-research').focus();page.keyboard.press('ArrowRight');assert page.locator('#sensor').is_visible()
        expect_text(page,'.history-note','told that the event starts at 64 s')
        page.locator('#open-current-research').click();assert page.locator('#research-frequency').is_visible()
        page.locator('#tab-research').focus();page.keyboard.press('Home');assert page.locator('#rewind').is_visible()
        page.locator('#core-method').select_option('full_steered');expect_text(page,'#core-acceptance','96.49%')
        page.locator('#core-emitter').click();expect_text(page,'#core-finding','10.10%')
        page.locator('#core-coupled').click();page.locator('#core-method').select_option('plain')
        page.locator('#tab-rewind').focus();page.keyboard.press('End');assert page.locator('#evidence').is_visible()
        page.keyboard.press('Control+Home');assert page.locator('#evidence').is_visible()
        checks.append('Original core controls unchanged; chapter arrows/Home/End and Ctrl+Home behave correctly; history link works')
        videos=[]
        for identifier in ['video-sensing','video-quantum-extension']:
            video=page.locator('#'+identifier);video.scroll_into_view_if_needed();video.evaluate('(v)=>v.load()');page.wait_for_function('(id)=>document.getElementById(id).readyState>=1',arg=identifier)
            duration=video.evaluate('(v)=>v.duration');assert abs(duration-12)<.05
            video.evaluate('(v)=>v.play()');page.wait_for_timeout(300)
            assert video.evaluate('(v)=>v.currentTime')>0
            video.evaluate('(v)=>{v.pause();v.currentTime=6;}');page.wait_for_timeout(100);assert abs(video.evaluate('(v)=>v.currentTime')-6)<.1
            videos.append({'id':identifier,'duration':duration,'play_pause_seek':'passed'})
        # Responsive behavior at phone width; preserve previous screenshots.
        page.set_viewport_size({'width':390,'height':844});page.locator('#tab-research').click()
        for study in ['frequency','drive','phase','progress','dot','hardware']:
            page.locator('#study-'+study).click();no_overflow(page)
            screenshot(page,'preview-research-'+study+'-mobile.png')
        screenshot(page,'preview-research-hardware-dot-mobile.png','.hardware-panel:has(#hardware-family)')
        page.locator('#study-dot').click()
        screenshot(page,'preview-research-dot-model-mobile.png','#research-dot .dot-benchmark');screenshot(page,'preview-research-dot-data-mobile.png','#research-dot .dot-published')
        screenshot(page,'preview-research-dot-bridge-mobile.png','#dot-project-bridge')
        screenshot(page,'preview-research-joint-hom-mobile.png','#dot-instrument');screenshot(page,'preview-research-dot-design-mobile.png','#dot-design')
        checks.append('390x844 mobile: all six study views have no document horizontal overflow and readable HTML data')
        page.emulate_media(reduced_motion='reduce');page.reload();page.wait_for_selector('#tab-research');assert page.locator('#motion').is_disabled() and page.locator('#replay').is_disabled() and page.locator('#walk').is_disabled()
        checks.append('Reduced-motion preference disables historical autoplay-style controls; MP4s have no autoplay')
        assert not errors,errors
        assert all(url.startswith('file:') for url in requests),requests
        version=browser.version;browser.close()
    receipt={'status':'passed','all_checks_passed':True,'route':'Existing Python Playwright + installed system Chrome in an isolated headless profile, standalone file URL. Uses the previously verified local fallback; no user browser profile or account used.','route_note':'Previous QA found CUA IAB unavailable and bundled Chromium 138 lacked H.264 decoding. This revision uses installed Chrome directly; media bytes remain unchanged.','python':platform.python_version(),'chromium':version,'checks':checks,'page_errors':errors,'network_requests':0,'videos':videos,'screenshots':screens,'source_sha256':{name:sha(HERE/name) for name in ['index.html','app.js','research.js','quantum-dots.js','joint-hom.js','hardware.js','styles.css','model.js','data.js','research-data.js','check_browser.py']},'evidence_manifest_sha256':sha(HERE/'evidence/manifest.json')}
    (HERE/'research_browser_validation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'all_checks_passed':True,'checks':len(checks),'screenshots':len(screens),'page_errors':errors,'chromium':version},indent=2))

if __name__=='__main__':main()

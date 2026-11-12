# Readme file for the dataset

The repository contains the data for the publication:  
J. Münzberg, F. Draxl, S.F. Covre da Silva, Y. Karli, S. Manna, A. Rastelli, G. Weihs, R. Keil, *Fast and efficient demultiplexing of single photons from a GaAs quantum dot with resonantly enhanced electro-optic modulators* (2022) ArXiv:XXXX.XXXXX [quant-ph]

Files containing the data to reproduce Fig. 2 of the publication:
- `As447_QD5_AB_ND2_no_pellicles.asc`:   
  Text file with the data to generate Fig. 2(a), line 1-34 is metadata containing the spectrometer and camera settings.
    - First column: Wavelength (nm)
    - Second column: Intensity (a.u.)
- `rabi_scan.csv`:   
  Text file containing the data to generate Fig. 2(b).  
    - First column: Set attenuation of the pump laser in the range from 0 to 1 (1 corresponding to no attenuation). An attenuation of 0.99 corresponds to a measured power of 2.1uW in front of the cryostat window. 
    - Second column: Detected countrate in Hz
    - Third column: Not used.
- `As447_QD5_resonant_no_AB_no_pellicles.asc`:  
  Text file containing the data to generate Fig. 2(c), line 1-34 is metadata containing the spectrometer and camera settings.
    - First column: Wavelength (nm)
    - Second column: Intensity (a.u.)
- `HBT_QD5_resonant_no_AB_att_0.0043_software_delay_16-44-38.csv`:  
  Text file containing the histogram data to generate Fig. 2(d).

Files containing the data to reproduce Fig. 3 of the publication:
- `QD5_phaseAdjustment_all_channels_18-05-50-photon1.csv`:  
  Text file containing the data to generate Fig. 3(a).
- `QD5_phaseAdjustment_all_channels_18-05-50-photon2.csv`:  
  Text file containing the data to generate Fig. 3(b).
- `QD5_phaseAdjustment_all_channels_18-05-50-photon3.csv`:  
  Text file containing the data to generate Fig. 3(c).
- `QD5_phaseAdjustment_all_channels_18-05-50-photon4.csv`:  
  Text file containing the data to generate Fig. 3(d).

Files containing the data to reproduce Fig. 4 of the publication:
- `HOM_QD5_resonant_photon1+2_17-39-23.csv`:  
  Text files containing the data to generate Fig. 4(a), Co-polarized
  `HOM_QD5_resonant_photon1+2_dist_17-42-16.csv`:  
  Text files containing the data to generate Fig. 4(a), Cross-polarized
- `HOM_QD5_resonant_photon1+3_17-50-06.csv`:  
  Text files containing the data to generate Fig. 4(b), Co-polarized
- `HOM_QD5_resonant_photon1+3_dist_17-52-41.csv`:  
  Text files containing the data to generate Fig. 4(b), Cross-polarized
- `HOM_QD5_resonant_photon1+4_17-57-10.csv`:  
  Text files containing the data to generate Fig. 4(c), Co-polarized
- `HOM_QD5_resonant_photon1+4_dist_18-00-48.csv`:  
  Text files containing the data to generate Fig. 4(c), Cross-polarized

File containing the data to reproduce Table I of the publication and Fig. S4 in the supplementary material:
- `QD5_countrates_18-06-15.csv`:  
  - Column 1: Unix timestamp in seconds when the data was recorded. 
  - Column 2 - 16: Number of detected events in an integration time of 1 second. The column labels correspond to the respective channel or coincidence channels.
  - The values reported in Table I are obtained from the raw data by calculating the mean value of each column 2 - 16 over all rows.

File containing the data to reproduce Fig. S1 in the supplementary material:
- `2021-03-18-slowEOM-F1--Trace--inPhase--000031.csv`:
  - line 1-5 is metadata
  - first column: Time (s)
  - second column: Voltage reading of the photodiode (V)

File containing the data to reproduce Fig. S2 in the supplementary material:
- `lifetime_QD5_resonant_no_AB_11-23-29.csv`:  
  Text file containing the histogram data recorded with the time tagger.

File containing the data to reproduce Fig. S3 in the supplementary material:
- `HBT_QD5_resonant_no_AB_att_0.0043_long_timescale_16-38-28.csv`  
  Text file containing the histogram data to generate Fig. S3(a).
- `HBT_QD5_resonant_AB_ND6_att_0.0043_software_delay_long_timescale_16-48-25.csv`  
  Text file containing the histogram data to generate Fig. S3(b).

File containing the data to reproduce Fig. S5 in the supplementary material:
- `scan_photon3_interferometer.csv`:
  - First column: Temporal delay (ps)
  - Second column: Minimally measured power
  - Third column: Maximally measured power
  - Fourth column: Average power
  - Fifth column: Standard deviation of the measured power

Files containing the data to reproduce Fig. S6 in the supplementary material:   

- `HOM_QD5_resonant_photon1+4_dist_14-27-05.csv`  
  Distinguishable case for all temperatures. 
- `HOM_QD5_resonant_only_photon1_HBT_14-20-58.csv`  
  HBT measurement at 8K. 
- `HOM_QD5_resonant_photon1_HBT_temp_8.7K_14-33-31.csv`  
  HBT measurement at 8.7K. 
- `HOM_QD5_resonant_photon1_HBT_temp_9.7K_14-39-06.csv`  
  HBT measurement at 9.7K. 
- `HOM_QD5_resonant_photon1_HBT_temp_10.7K_14-43-23.csv`  
  HBT measurement at 10.7K. 
- `HOM_QD5_resonant_photon1_HBT_temp_12.7K_14-45-26.csv`  
  HBT measurement at 12.7K. 
- `HOM_QD5_resonant_photon1+4_temp_8K_14-29-45.csv`  
  HOM measurement at 8K. 
- `HOM_QD5_resonant_photon1+4_temp_8.7K_14-34-55.csv`  
  HOM measurement at 8.7K. 
- `HOM_QD5_resonant_photon1+4_temp_9.7K_14-36-51.csv`  
  HOM measurement at 9.7K.
- `HOM_QD5_resonant_photon1+4_temp_10.7K_14-41-40.csv`  
  HOM measurement at 10.7K.
- `HOM_QD5_resonant_photon1+4_temp_12.7K_14-53-38.csv`  
  HOM measurement at 12.7K.
   

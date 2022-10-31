# Pirate-Weather-SMSL
Repository containing example code for processing GRIB files on AWS into chunked NetCDF files. Adapted from the [aws-nexrad-smsl-notebook](https://github.com/aws-samples/aws-nexrad-smsl-notebook/).

## AWS SageMaker Studio Lab
You can sign up for SageMaker Studio Lab and use it for free without an AWS account. You can run for 4 hours with GPU or 12 hours with CPU and then logout and log back in for another session. Your data and notebooks are persisted. After clicking the launch button below, choose "download whole repo" and then "build conda environment" when prompted.

When it's done installing and configuring the conda environment (this can take several minutes), open the "Pirate_HRRR_SM_Notebook.ipynb" notebook.  Click-Enter to run each row and wait a moment to see the results of each line before proceeding to the next. The line marker should change to a number when it's successfully run that line, ie "[5]" means that it has run line 5.

## Script Outline

The example script flows through the steps used in the [Pirate Weather API](https://pirateweather.net/). This script downloads raw NOAA weather forecast model results from S3 in a format called GRIB. It then extracts key variables from these files and saves them as chunked NetCDF files. Finally, the notebook extracts the forecasted temperatures at a latitude and longitude in contenental United States. 


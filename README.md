# sca-codeinsight-reports-installer

The `sca-codeinsight-reports-installer` repository allows users to easily install available reports into the Code Insight report framework

## Prerequisites


**Python Requirements**

A minimum vesion of python 3.5 is required to run this script.  The required python modules can be installed with the use of the [requirements.txt](requirements.txt) file which can be loaded via.

	pip install -r requirements.txt

## Usage

The script accepts three arguments to be supplied by the user
- The Code Insight installation directory
- The URL/FQDN of the Code Insight system
- An admin authorization token to be used when registering the report into Code Insight  

To run the script on a windows system
    
	python install_reports.py -server ${Server URL} -token ${Admin Auth Token} -installDir $(CodeInsight Install Directory}

To run the script on a Linux system
    
	python3 install_reports.py -server ${Server URL} -token ${Admin Auth Token} -installDir $(CodeInsight Install Directory}

The [install_reports.py](install_reports.py) script will

- Verify the installation directory supplied or if the current working directory is a valid Code Insight installation
- Create the custom_report_scripts directory if required
- Determine if a server.properties.json file exists and attempt to create this file based on the supplied argumetns if possible.
- Recursivly clone the supplied report repositories
- Install any needed python dependencies using the requiremetns.txt file
    - sudo user permissions maybe required on linux systems
- Register the report with Code Insight
- Display the current versions of all of the reports installed by the script



## License

[MIT](LICENSE)
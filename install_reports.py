'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Mon Nov 08 2021
File : install_reports.py
'''
import sys
import os
import logging
import argparse
import json
from git import Repo
import subprocess


repositories = []
repositories.append("https://github.com/flexera/sca-codeinsight-reports-project-inventory.git")
repositories.append("git@github.com:flexera/sca-codeinsight-reports-project-sbom.git")

propertiesFileName = "server_properties.json"

###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info <= (3, 7):
    raise Exception("The current version of Python is less than 3.5 which is unsupported.\n Script created/tested against python version 3.8.1. ")
else:
    pass

logfileName = os.path.dirname(os.path.realpath(__file__)) + "/_install_reports.log"


###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)-3d  %(levelname)-8s [%(filename)-30s:%(lineno)-4d]  %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module



####################################################################################
# Create command line argument options
parser = argparse.ArgumentParser()
parser.add_argument('-server', "--server", help="Code Insight server URL")
parser.add_argument("-token", "--token", help="Auth token with admin access")
parser.add_argument("-installDir", "--installationDirctory", help="Code Insight base installation folder?")


#------------------------------------------------------------------------------------------------------------------------------
def main():

    # See what if any arguments were provided
    args = parser.parse_args()
    serverURL = args.server
    adminAuthToken = args.token
    installDir = args.installationDirctory

    # verify the supplied installDir or current directoyr is valid
    reportInstallationFolder = verify_installation_directory(installDir)

    if reportInstallationFolder:
        logger.info("%s is a valid folder for report installation" %reportInstallationFolder)
        print("%s is a valid folder for report installation" %reportInstallationFolder)

    else:
        logger.info("Unable to determine valid Code Insight install folder for reports")
        print("Unable to determine valid Code Insight install folder for reports")


#-------------------------------------------------------------------
def verify_installation_directory(installDir):
    logger.info("Entering verify_installation_directory")

    # Was a directory supplied and if so is it valid?
    if  installDir:
        if os.path.isdir(installDir):
            logger.info("    Supplied directory %s  does exist" %installDir)
        else:
            logger.error("    Supplied directory %s does not exist" %installDir)
            return None

    else:
        logger.info("No installation directory passed.  Using current directory.")
        installDir = os.path.dirname(os.path.realpath(__file__))  # Get the current folder
        logger.info("Current directory: %s" %installDir)


    # At this point we are assuming we have the Code Insight instllation folder or possibly the custom_report_scripts folder
    if installDir.endswith("custom_report_scripts"):
        logger.info("The customer_report_script directory could have been passed directly")
        installDir = installDir[:-22]  # Strip off custom_report_scripts part
    

    # A list of folders that we expect to see within the Code Insight base instllation folder
    expectedFolders = ["tomcat", "jre", "logs", "7-zip", "dbScripts"]
    folders = os.listdir(installDir)

    if not set(expectedFolders).issubset(set(folders)):
        # This doesn't look like a Code Insight folder
        logger.error("This does not appear to be a Code Insight installation")
        return None

    reportInstallationFolder = os.path.join(installDir, "custom_report_scripts")

    # Does the custom_report_scripts folder exist?
    if os.path.isdir(reportInstallationFolder):
        logger.info("reportInstallationFolder already exists")
    else:
        os.mkdir(reportInstallationFolder) 

    return(reportInstallationFolder)

#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  
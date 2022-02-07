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
import subprocess

repositories = []
repositories.append("https://github.com/flexera-public/sca-codeinsight-reports-project-inventory.git")
repositories.append("https://github.com/flexera-public/sca-codeinsight-reports-project-sbom.git")
repositories.append("https://github.com/flexera-public/sca-codeinsight-reports-project-vulnerabilities.git")
repositories.append("https://github.com/flexera-public/sca-codeinsight-reports-spdx.git")
repositories.append("https://github.com/flexera-public/sca-codeinsight-reports-third-party-evidence.git")
repositories.append("https://github.com/flexera-public/sca-codeinsight-reports-project-comparison.git")
repositories.append("https://github.com/flexera-public/sca-codeinsight-reports-claim-files.git")

propertiesFileName = "server_properties.json"

###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info <= (3, 6):
    raise Exception("The current version of Python is less than 3.5 which is unsupported.\n Script created/tested against python version 3.8.1. ")
else:
    pass

logfileName = os.path.dirname(os.path.realpath(__file__)) + "/_install_reports.log"

reportRequirementsFile = "requirements.txt"
reportRegistrationFile = "registration.py"
gitCloneCommandBase = "git clone --recursive"
gitPullCommand = "git pull --recurse-submodules"
gitDescribeCommand = "git describe"

# Based on how the shell pass the arguemnts clean up the options if on a linux system
if sys.platform.startswith('linux'):
    pythonCommand = "python3"
    pipCommand = "sudo pip3"
else:
    pythonCommand = "python"
    pipCommand = "pip"    


###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)-3d  %(levelname)-8s [%(filename)-30s:%(lineno)-4d]  %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module

####################################################################################
# Create command line argument options
parser = argparse.ArgumentParser()
parser.add_argument('-server', "--server", help="Code Insight server URL - http(s)://FQDN:port")
parser.add_argument("-token", "--token", help="Auth token with admin access", required=True)
parser.add_argument("-installDir", "--installationDirctory", help="Code Insight base installation folder?")

#------------------------------------------------------------------------------------------------------------------------------
def main():

    # See what if any arguments were provided
    args = parser.parse_args()
    serverURL = args.server
    adminAuthToken = args.token
    installDir = args.installationDirctory

    reportVersions = {}

    # verify the supplied installDir or current directoyr is valid
    reportInstallationFolder = verify_installation_directory(installDir)

    if reportInstallationFolder:
        logger.info("%s is a valid folder for report installation" %reportInstallationFolder)
        print("%s is a valid folder for report installation" %reportInstallationFolder)

    else:
        logger.error("Unable to determine valid Code Insight install folder for reports")
        print("Unable to determine valid Code Insight install folder for reports")
        return

    propertiesFile = os.path.join(reportInstallationFolder, propertiesFileName)

    # Does a properties file already exist? 
    propertiesFile = verify_properties_file(serverURL, adminAuthToken, propertiesFile)

    if not propertiesFile:
        logger.error("Invalid server properties file details")
        print("Invalid server properties file details")
        return

    # Now install the reports
    for repository in repositories:
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++")
        logger.info("    Installing: %s" %repository)
        print("    Installing: %s" %repository)

        reportName = repository.split("/")[-1].split(".")[0]  # Remove the base and .git from the repo name
        reportFolder = os.path.join(reportInstallationFolder, reportName)

        # Does the directory repo already exist?
        if os.path.isdir(reportFolder):
            logger.info("        The report folder for %s already exists. Checking for updates." %reportName)
            print("        The report folder for %s already exists. Checking for updates." %reportName)

            os.chdir(reportFolder)
            pullResponse = subprocess.run(gitPullCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            if "Already up to date." in pullResponse.stdout.decode():
                logger.info("        The latest updates are already available.")
                print("        The latest updates are already available.")

            else:

                logger.info("        Latest updates have been pulled.")
                print("        Latest updates have been pulled.")
                
                # Since there was an update verify requiremetns are met
                sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
                logger.info("        Updating requirements")
                print("        Updating requirements")
                requirementsCommand = pipCommand + " install -r " + reportRequirementsFile
                requirementsResponse = subprocess.run(requirementsCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                logger.debug(requirementsResponse.stdout.decode())
                
                # Since there was an update update the registration
                sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
                logger.info("        Updating report registration for %s" %reportName)
                print("        Updating report registration for %s" %reportName)
                registrationCommand = pythonCommand + " " + reportRegistrationFile + " -update"
                registrationResponse = subprocess.run(registrationCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                logger.debug(registrationResponse.stdout.decode())

        else:
            logger.info("        Cloning (recursively) %s" %repository)
            print("        Cloning (recursively) %s" %repository)

            sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
            # Clone the repsoitory and bring in the submodules
        
            gitCloneCommand = gitCloneCommandBase + " " + repository + " " + reportFolder

            cloneResponse = subprocess.run(gitCloneCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logger.debug(cloneResponse.stdout.decode())

            requirementsCommand = pipCommand + " install -r " + reportRequirementsFile
            registrationCommand = pythonCommand + " " + reportRegistrationFile + " -reg"
            os.chdir(reportFolder)

            sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
            logger.info("        Installing requirements")
            print("        Installing requirements")
            requirementsResponse = subprocess.run(requirementsCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logger.debug(requirementsResponse.stdout.decode())

            sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
            logger.info("        Registering report %s" %reportName)
            print("        Registering report %s" %reportName)
            registrationResponse = subprocess.run(registrationCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logger.debug(registrationResponse.stdout.decode())

        # Collect the report version for summary
        reportVersion = subprocess.check_output(gitDescribeCommand, shell=True)
        reportVersions[reportName] = reportVersion.rstrip().decode()

        os.chdir(reportInstallationFolder)  # Go back to the custom_report_scripts folder for the next iteration

    #----------------------------------------------


    print("**************************************")
    print("Currently Installed Reports")
    for report in sorted(reportVersions):

        print(f"    {report:50} - {reportVersions[report]:10}")

    # Now that that reports are installed remove the token from the properties file
    sanitize_properties_file(propertiesFile)


#-------------------------------------------------------------------
def verify_installation_directory(installDir):
    logger.info("Entering verify_installation_directory")

    # Was a directory supplied and if so is it valid?
    if installDir:
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

#-------------------------------------------------------------------
def verify_properties_file(serverURL, adminAuthToken, propertiesFile):
    logger.info("Entering verify_properties_file")

   
    # Does the properties file alrady exist?
    if not os.path.isfile(propertiesFile):
        logger.info("    The properties file does not currently exist")

        # Were values passed by the users?
        if serverURL and adminAuthToken:

            # Deal with server configuration values
            serverDetails={}
            serverDetails["core.server.url"]=serverURL
            serverDetails["core.server.token"]=adminAuthToken

            print("    Creating properties file: %s" %propertiesFile)
            filePtr = open(propertiesFile, 'w')
            json.dump(serverDetails, filePtr)
            filePtr.close

        else:
            logger.error("    The URL or token values were not provided")
            print("    The URL or token values were not provided")
            return None

    else:
        logger.info("    %s already exists" %propertiesFile)
        print("    %s already exists" %propertiesFile)

        # Open the file up to see what's there and compare to what's provided
        filePtr = open(propertiesFile, "r")
        configData = json.load(filePtr)
        filePtr.close

        # Always update the server URL
        configData["core.server.url"]=serverURL
            
        # Is there already a token if so back it up to restore later 
        if "core.server.token" in configData:
            configData["core.server.token.orig"] = configData["core.server.token"]

        configData["core.server.token"] = adminAuthToken

        # Now write the data back to the file
        print("    Updating properties file: %s" %propertiesFile)
        filePtr = open(propertiesFile, 'w')
        json.dump(configData, filePtr)
        filePtr.close

    return propertiesFile

    #TODO  Check the values passed to values in the file currently and prompt for update if needed

#-------------------------------------------------------------------
def sanitize_properties_file(propertiesFile):
    logger.info("Entering sanitize_properties_file")

    # Open the file up to see what's there and compare to what's provided
    filePtr = open(propertiesFile, "r")
    configData = json.load(filePtr)
    filePtr.close

    # Is there already a token if so back it up to restore later 
    if "core.server.token.orig" in configData:
        configData["core.server.token"] = configData["core.server.token.orig"]
        configData.pop("core.server.token.orig")
    else:
        configData.pop("core.server.token")

    # Now write the data back to the file
    print("    Updating properties file: %s" %propertiesFile)
    filePtr = open(propertiesFile, 'w')
    json.dump(configData, filePtr)
    filePtr.close    

    logger.info("Exiting sanitize_properties_file")

   



#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  
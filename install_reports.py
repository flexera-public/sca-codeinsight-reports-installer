'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Mon Nov 08 2021
File : install_reports.py
'''
import sys, os, logging, argparse, json
import requests, subprocess, shutil, stat

import report_repositories

propertiesFileName = "server_properties.json"

###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info < (3, 6):
    raise Exception("The current version of Python is less than 3.6 which is unsupported.\n Script created/tested against python version 3.6.18 ")
else:
    pass

installerDirectory = os.path.dirname(os.path.realpath(__file__))
logfileName = "_" + os.path.basename(__file__).split('.')[0] + ".log"
defaultRegistrationLogFileName = "_registration.log" # Default log name for report registration scripts

###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)-3d  %(levelname)-8s [%(filename)-30s:%(lineno)-4d]  %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)

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


####################################################################################
# Create command line argument options
parser = argparse.ArgumentParser()
parser.add_argument('-server', "--server", help="Code Insight server URL - http(s)://FQDN:port")
parser.add_argument("-token", "--token", help="Auth token with admin access")
parser.add_argument("-installDir", "--installationDirctory", help="Code Insight base installation folder?")
parser.add_argument("-certificatePath", "--certificatePath", help="Path to self signed certificate")

#------------------------------------------------------------------------------------------------------------------------------
def main():

    reportVersions = {}

    args = parser.parse_args()

    systemDetails = validate_arguments(args)

    reportInstallationFolder = systemDetails["reportInstallationFolder"]
    propertiesFile = systemDetails["propertiesFile"]
   
    # Create or update the properties files since the report registration script uses it 
    manage_properties_file(systemDetails)

    # Now install the reports
    for repository in report_repositories.repositories:
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

            if "Already up to date." in pullResponse.stdout.decode() or  "Already up-to-date" in pullResponse.stdout.decode():
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

            requirementsCommand = pipCommand + " install -r " + reportRequirementsFile + " --quiet"
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
            
            if "Report registration succeeded!" in registrationResponse.stdout.decode():
                print("        The report has been reigstered")
                logging.info("        The report has been reigstered")

            elif "Report registration failed!" in registrationResponse.stdout.decode():
                logger.error(registrationResponse.stdout.decode())
                print("        There was a probem encountered while attempting to register the report")
                print("            %s" %registrationResponse.stdout.decode())

                # Copy the installation log file to the installer directory
                if os.path.isfile(defaultRegistrationLogFileName):
                
                    movedLogFile = os.path.join(installerDirectory, reportName + "_installation.log")
                    logger.info("Moving report registration logfile to %s" %movedLogFile)
                    try:
                        shutil.copyfile(defaultRegistrationLogFileName, movedLogFile)
                    except:
                        logger.error("Unable to copy logfile to %s" %movedLogFile)
                else:
                    logger.error("Log file does not exist: %s" %defaultRegistrationLogFileName)

                os.chdir(reportInstallationFolder)

                try:
                    shutil.rmtree(reportFolder, onerror=change_file_read_attribute)
                    print("        Removing folder: %s" %reportFolder)
                except:
                    print("        Manually remove folder: %s" %reportFolder)
                print("        Verify server/token information and attempt to install again") 
                sanitize_properties_file(propertiesFile)              
                sys.exit()
            else:
                print("        Unknown response while attempting to register report")
                logger.error("        Unknown response while attempting to register report")
                logger.error(registrationResponse.stdout.decode())


        # Collect the report version for summary
        reportVersion = subprocess.check_output(gitDescribeCommand, shell=True)
        reportVersions[reportName] = reportVersion.rstrip().decode()

        # Copy the installation log file to the installer directory
        if os.path.isfile(defaultRegistrationLogFileName):
        
            movedLogFile = os.path.join(installerDirectory, reportName + "_installation.log")
            logger.info("Moving report registration logfile to %s" %movedLogFile)
            print("        Moving report registration logfile to %s" %movedLogFile)
            try:
                shutil.copyfile(defaultRegistrationLogFileName, movedLogFile)
            except:
                logger.error("Unable to copy logfile to %s" %movedLogFile)
                print("Unable to copy logfile to %s" %movedLogFile)

        else:
            print("Log file does not exist: %s" %defaultRegistrationLogFileName)
            logger.error("Log file does not exist: %s" %defaultRegistrationLogFileName)

        os.chdir(reportInstallationFolder)  # Go back to the custom_report_scripts folder for the next iteration

    #----------------------------------------------
    # Now that that reports are installed remove the token from the properties file
    sanitize_properties_file(propertiesFile)
    
    print("")
    print("**************************************")
    print("Currently Installed Reports")
    for report in sorted(reportVersions):

        print(f"    {report:50} - {reportVersions[report]:10}")


#------------------------------------------------------------
def validate_arguments(args):

    installDir = args.installationDirctory
    serverURL = args.server
    adminAuthToken = args.token
    certificatePath = args.certificatePath

    systemDetails = {}

    # Verify the Code Insight installation to ensure there is a location for the reports to go
    reportInstallationFolder =  verify_installation_directory(installDir)
    if "error" in reportInstallationFolder:
        print(reportInstallationFolder["error"])
        sys.exit()
    
    # Now that we know th location is there already an existing properties file we can use?
    propertiesFile = os.path.join(reportInstallationFolder, propertiesFileName)

    # Does the properties file alrady exist?
    if os.path.isfile(propertiesFile):
        logger.info("    Properties file %s was found" %propertiesFile)
        print("    Properties file %s was found" %propertiesFile)
        
        # Open the file up to see what's there and compare to what's provided
        filePtr = open(propertiesFile, "r")
        configData = json.load(filePtr)
        filePtr.close
    else:
        logger.info("    The properties file does not currently exist. Relying on command line arugments")
        print("    The properties file does not currently exist. Relying on command line arugments")
        configData = {}

    if serverURL is None:
        # There was no server information passed so check configData    
        if "core.server.url" in configData:
            if configData["core.server.url"] is None:
                logger.error("    The Code Insight Server URL was not provided and is not contained in the properties file")
                logger.error("               Please provide the server and port URL via the -server flag")
                print("    **ERROR**  The Code Insight Server URL was not provided and is not contained in the properties file")
                print("               Please provide the server and port URL via the -server flag")
                sys.exit()
            else:
                serverURL = configData["core.server.url"]
                print("    Using server details from properties file:  %s" %serverURL)
                logger.info("    Using server details from properties file:  %s" %serverURL)
        else:
            logger.error("               Server details not in properties file.  Please provide the server details via the -server flag")
            print("    **ERROR**  Server details not in properties file.  Please provide the server details via the -server flag")
            sys.exit()

    else:
        if serverURL.endswith("/"):
            serverURL = serverURL[:-1]

        print("    Using server details provided as argurment: %s" %serverURL)
        logger.info("    Using server details provided as argurment: %s" %serverURL)

    if adminAuthToken is None:
        # There was no token information passed so check configData    
        if "core.server.token" in configData:
            if configData["core.server.token"] is None:
                logger.error("    **ERROR**  The Code Insight Admin authorization token was not provided and is not contained in the properties file")
                logger.error("               Please provide the admin auth token the -token flag")
                print("    **ERROR**  The Code Insight Admin authorization token was not provided and is not contained in the properties file")
                print("               Please provide the admin auth token the -token flag")
                sys.exit()
            else:
                adminAuthToken = configData["core.server.token"]
                print("    Using autorization token from properties file.")
                logger.info("    Using autorization token from properties file.")
        else:
            logger.error("               Token details not in properties file.  Please provide the token details via the -token flag")
            print("    **ERROR**  Token details not in properties file.  Please provide the token details via the -token flag")
            sys.exit()
    else:
        print("    Using autorization token provided as argurment.")
        logger.info("    Using autorization token provided as argurment.")

    # Get the Code Insight release details to determine if the server and token are valid
    releaseDetails = get_release_details(serverURL, adminAuthToken)

    if "fnci.release.name" in releaseDetails:
        releaseVersion = releaseDetails["fnci.release.name"]
        print("    Successfully verified connection to Code Insight server")
        print("      -  Code Insight Version: %s" %releaseVersion)
    elif "error" in releaseDetails:
        errorMessage = str(releaseDetails["error"])
        
        if "Max retries exceeded" in errorMessage:
            message = '''** There appears to be an issue commuincatiing with the Code Insight Server.  \n    ** Please check the host and port values.'''
            logger.error("    %s" %message)
            print("    %s" %message)

        elif "Unauthorized" in errorMessage:
            message = '''** The host and port values appear to be correct but the authorization token is not valid.  \n    ** Please check the token and ensure the user has admistrative perimssions.'''
            logger.error("    %s" %message)
            print("    %s" %message)

        else:
            print("Unhandled exception.  Please check log for details")
            logger.error(errorMessage)
       
        print("Exiting installer")
        sys.exit()

    else:
        logger.error("Unknown Error: %s" %releaseDetails)
        print("    Exiting installer due to unknown error. Please see log for details")

    try:

        certificatePath = os.path.normpath(certificatePath)
        os.environ["REQUESTS_CA_BUNDLE"] = certificatePath
        os.environ["SSL_CERT_FILE"] = certificatePath
        logger.info("Self signed certificate provied as argument")
    except:
        logger.info("No self signed certificate was provied as argument")
        certificatePath = None

    systemDetails = {}
    systemDetails["releaseVersion"] = releaseVersion
    systemDetails["reportInstallationFolder"] = reportInstallationFolder
    systemDetails["propertiesFile"] = propertiesFile
    systemDetails["serverURL"] = serverURL
    systemDetails["adminAuthToken"] = adminAuthToken
    systemDetails["certificatePath"] = certificatePath

    return systemDetails

#-------------------------------------------------------------------
def verify_installation_directory(installDir):
    logger.info("Entering verify_installation_directory")

    # Was a directory supplied and if so is it valid?
    if installDir:

        if os.path.isdir(installDir):
            # make the path an absolute path
            installDir =os.path.abspath(installDir)
            logger.info("    Supplied directory %s does exist" %installDir)
        else:
            logger.error("    Supplied directory %s does not exist" %installDir)
            return {"error" : "The supplied directory of %s does not exist on this system." %installDir}

    else:
        logger.info("No installation directory passed.  Using current directory.")
        installerDir = os.path.dirname(os.path.realpath(__file__))  # Get the current folder of the installer
        print("No installation directory passed.  Attempting to use current location to determine installation directory.")
        logger.info("No installation directory passed.  Attempting to use current location to determine installation directory.")

        installDir = (os.path.dirname(installerDir))

    # At this point we are assuming we have the Code Insight installation folder or possibly the custom_report_scripts folder
    if installDir.endswith("custom_report_scripts"):
        logger.info("The customer_report_script directory could have been passed directly")
        installDir = (os.path.dirname(installDir))  

    # A list of folders that we expect to see within the Code Insight base instllation folder
    expectedFolders = ["tomcat", "jre", "logs", "7-zip", "dbScripts"]
    folders = os.listdir(installDir)

    if not set(expectedFolders).issubset(set(folders)):
        # This doesn't look like a Code Insight folder
        logger.error("This does not appear to be a Code Insight installation")
        return {"error" : "The directory %s does not appear to be a Code Insight installation." %installDir}

    reportInstallationFolder = os.path.join(installDir, "custom_report_scripts")

    # Does the custom_report_scripts folder exist?
    if os.path.isdir(reportInstallationFolder):
        logger.info("reportInstallationFolder already exists")
    else:
        os.mkdir(reportInstallationFolder) 
    
    logger.info("Report Installation Folder: %s" %reportInstallationFolder)

    return(reportInstallationFolder)

#-------------------------------------------------------------------
def manage_properties_file(systemDetails):
    logger.info("Entering manage_properties_file")

    propertiesFile = systemDetails["propertiesFile"]
    serverURL = systemDetails["serverURL"]
    adminAuthToken = systemDetails["adminAuthToken"]
    certificatePath =  systemDetails["certificatePath"]

    # Deal with server configuration values
    serverDetails={}
    serverDetails["core.server.url"]=serverURL
    serverDetails["core.server.token"]=adminAuthToken
    serverDetails["core.server.certificate"]=certificatePath

    # Does the properties file alrady exist?
    if not os.path.isfile(propertiesFile):
        print("    Creating properties file: %s" %propertiesFile)
    else:
        print("    Updating properties file: %s" %propertiesFile)

    filePtr = open(propertiesFile, 'w')
    json.dump(serverDetails, filePtr, indent=4)
    filePtr.close



#----------------------------------------------------
def get_release_details(baseURL, authToken):
    logger.debug("Entering get_release_details.")

    RESTAPI_BASEURL = "%s/codeinsight/api" %(baseURL)
    RESTAPI_URL = "%s/v1/agent/supports" %(RESTAPI_BASEURL)

    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken}   

    ##########################################################################   
    # Make the REST API call with the project data           
    try:
        response = requests.get(RESTAPI_URL, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        return {"error" : error}

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        releaseDetails = json.loads(response.json()["Content: "])
        return releaseDetails
    else:
        return {"error" : response.text}




#-------------------------------------------------------------------
def sanitize_properties_file(propertiesFile):
    logger.info("Entering sanitize_properties_file")
    logger.info("Taking no action to mask token from file")
    logger.info("Exiting sanitize_properties_file")
    return

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
def change_file_read_attribute(func, path, exc_info):
    os.chmod( path, stat.S_IWRITE )
    os.unlink( path )


#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  
#!/usr/bin/env python
import os,sys,urllib2,platform,re,zipfile,hashlib,glob

# check if root with geteuid
if os.geteuid() != 0:
    print "Please re-run this script with root privileges, i.e. 'sudo ./install.py'\n"
    sys.exit()

# check if running on Mac
mac = (platform.system() == 'Darwin')

# check if all necessary system utilities are present
if mac:
    exitcode = os.system("which clear diskutil grep dd")
else:
    exitcode = os.system("which clear fdisk grep umount mount cut dd blockdev")
if exitcode != 0:
    print "Error: your operating system does not include all the necessary utilities to continue."
    if mac:
        print "Utilities necessery: clear diskutil grep dd"
    else:
        print "Utilities necessery: clear fdisk grep umount mount cut dd blockdev"
    print "Please install them."
    sys.exit()

os.system("clear")
print "Cubietruck Debian installer for Linux and OS X"
print "http://www.igorpecovnik.com/2013/12/24/cubietruck-debian-wheezy-sd-card-image/"
print "----------------------------------------"

# yes/no prompt adapted from http://code.activestate.com/recipes/577058-query-yesno/
def query_yes_no(question, default="yes"):
    valid = {"yes":"yes", "y":"yes", "ye":"yes", "no":"no", "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)
    while 1:
        print question + prompt
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            print "Please respond with 'yes' or 'no' (or 'y' or 'n').\n"

def chunk_report(bytes_so_far, chunk_size, total_size):
    percent = float(bytes_so_far) / total_size
    percent = round(percent*100, 2)
    sys.stdout.write("Downloaded %0.2f of %0.2f MiB (%0.2f%%)\r" %
        (float(bytes_so_far)/1048576, float(total_size)/1048576, percent))
    if bytes_so_far >= total_size:
        sys.stdout.write('\n')

def chunk_read(response, file, chunk_size, report_hook):
    total_size = response.info().getheader('Content-Length').strip()
    total_size = int(total_size)
    bytes_so_far = 0
    while 1:
        chunk = response.read(chunk_size)
        file.write(chunk)
        bytes_so_far += len(chunk)
        if not chunk:
            break
        if report_hook:
            report_hook(bytes_so_far, chunk_size, total_size)
    return bytes_so_far

def download(url):
    print "Downloading, please be patient..."
    dl = urllib2.urlopen(url)
    dlFile = open(extractZipNameFromUrl(url), 'w')
    chunk_read(dl, dlFile, 8192, chunk_report)
    #dlFile.write(dl.read())
    dlFile.close()

def deviceinput():
    # they must know the risks!
    verified = "no"
    raw_input("Please ensure you've inserted your SD card, and press Enter to continue.")
    while verified is not "yes":
        print ""
        if mac:
            print "Enter the 'IDENTIFIER' of the device you would like imaged:"
        else:
            print "Enter the 'Disk' you would like imaged, from the following list:"
        listdevices()
        print ""
        if mac:
            device = raw_input("Enter your choice here (e.g. 'disk1', 'disk2'): ")
        else:
            device = raw_input("Enter your choice here (e.g. 'mmcblk0' or 'sdd'): ")
        # Add /dev/ to device if not entered
        if not device.startswith("/dev/"):
            device = "/dev/" + device
        if os.path.exists(device) == True:
            print "It is your own responsibility to ensure there is no data loss! Please backup your system before imaging"
            cont = query_yes_no("Are you sure you want to install Cubietruck Debian to '\033[31m" + device + "\033[0m'?", "no")
            if cont == "no":
                sys.exit()
            else:
                verified = "yes"
        else:
            print "Device doesn't exist"
            # and thus we are not 'verified'
            verified = "no"
    return device

def listdevices():
    if mac:
        print "   #:                       TYPE NAME                    SIZE       IDENTIFIER"
        os.system('diskutil list | grep "0:"')
    else:
        os.system('fdisk -l | grep -E "Disk /dev/"')

def unmount(drive): # unmounts drive
    print "Unmounting all partitions..."
    if mac:
        exitcode = os.system("diskutil unmountDisk " + drive)
    else:
        # check if partitions are mounted; if so, unmount
        if os.system("mount | grep " + drive + " > /dev/null") == 0:
            exitcode = os.system("umount `mount | grep " + drive + " | cut -f1 -d ' '`")
        else:
            # partitions were not mounted; must pass error check
            exitcode = 0
    if exitcode != 0:
        print 'Error: the drive couldn\'t be unmounted, exiting...'
        sys.exit()

def imagedevice(drive, imagefile):
    print ""
    rawFilename = unzipImage(imagefile)
    unmount(drive)
    # use the system's built in imaging and extraction facilities
    print "Please wait while Cubietruck Debian is installed to your SD card..."
    print "This may take some time and no progress will be reported until it has finished."
    if mac:
        os.system("dd if=" + rawFilename + " of=" + drive + " bs=1m")
    else:
        os.system("dd if=" + rawFilename + " of=" + drive + " bs=1M")
        # Linux kernel must reload the partition table
        os.system("blockdev --rereadpt " + drive)
    print "Installation complete."

#extract and check md5
def unzipImage(imagefile):
    rawFilename = imagefile[:-3] + "raw"
    md5Filename = imagefile[:-3] + "md5"

    print "Extract data this may take some time and no progress will be reported until it has finished"
    zipfile.ZipFile(imagefile, "r").extractall()

    with open (md5Filename, "r") as md5File:
      data = md5File.readline().replace('\n', '')
      data = re.search(r"(.*)\s", data).group(1).strip()
      md5File.close()

    if(data != checksum_md5(imagefile[:-3] + "raw")):
      print "Ooooppsss wrong checksum please restart download"
      sys.exit()

    return rawFilename

def extractZipNameFromUrl(url):
  return re.search(r"/(Cubietruck.*)", url).group(1)

#http://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
def checksum_md5(filename, block_size=2**20):
    md5 = hashlib.md5()
    with open(filename,'rb') as f:
        for chunk in iter(lambda: f.read(block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()

def cubieinstaller():
    baseUrl = "http://mirror.igorpecovnik.com/"
    # configure the device to image
    disk = deviceinput()
    # should downloading and extraction be done?
    redl = "" # so that redl == "yes" doesn't throw an error
    listCTDebianZips = glob.glob('Cubietruck*.zip')
    debianZipExist = (len(listCTDebianZips) != 0)
    debianZipToInstall = ""
    if debianZipExist:
        redl = query_yes_no("It appears that the Cubietruck installation image has already been downloaded. Would you like to re-download it?", "no")
    if redl == "yes" or len(listCTDebianZips) == 0:
        list = []
        count = 1;
        for (url, desc) in re.findall('''href=["](.*Cubietruck[^"]+)["]>(.[^"]+)</a>''', urllib2.urlopen(baseUrl).read(), re.I):
          list.append(url)
          print "{}) {}".format(count, desc)
          count = count + 1

        var = input("Which version (1 - {}): ".format(len(list)))
        val = int(var) - 1
        debianZipToInstall = list[val]
        # call the dl
        download(baseUrl + list[val])
    # now we can image
    if mac:
        regex = re.compile('/dev/r?(disk[0-9]+?)')
        try:
            disk = re.sub('r?disk', 'rdisk', regex.search(disk).group(0))
        except:
            print "Malformed disk specification -> ", disk
            sys.exit()
    if redl == "no" and debianZipExist:
      debianZipToInstall = listCTDebianZips[0];

    imagedevice(disk, debianZipToInstall)

    print ""
    print "Debian Cubietruck is now ready, please insert the SD card into your Cubietruck"
    print ""

cubieinstaller()

# Chatter

Chatter is a tool designed to be a self-hosted chat cog.

It is based on the brilliant work over at [Chatterbot](https://github.com/gunthercox/ChatterBot) and [spaCy](https://github.com/explosion/spaCy)


## Known Issues

* Chatter will not reload
    * Causes this error:
    ```
    chatterbot.adapters.Adapter.InvalidAdapterTypeException: chatterbot.storage.SQLStorageAdapter must be a subclass of StorageAdapter 
    ```
* Chatter responses are slow
    * This is an unfortunate side-effect to running self-hosted maching learning on a discord bot. 
    * This version includes a number of attempts at improving this, but there is only so much that can be done.
* Chatter responses are irrelevant
    * This can be caused by bad training, but sometimes the data just doesn't come together right.
    * Asking for better accuracy often leads to slower responses as well, so I've leaned towards speed over accuracy.
* Chatter installation is not working
    * See installation instructions below

## Warning

**Chatter is a CPU, RAM, and Disk intensive cog.**

Chatter by default uses spaCy's `en_core_web_md` training model, which is ~50 MB

Chatter can potential use spaCy's `en_core_web_lg` training model, which is ~800 MB

Chatter uses as sqlite database that can potentially take up a large amount os disk space,
depending on how much training Chatter has done. 

The sqlite database can be safely deleted at any time. Deletion will only erase training data.


# Installation
The installation is currently very tricky, and only tested on a Windows Machine. 

There are a number of reasons for this, but the main ones are as follows:
* Using a dev version of chatterbot
* Some chatterbot requirements conflict with Red's (as of 3.10)
* spaCy version is newer than chatterbot's requirements
* A symlink in spacy to map `en` to `en_core_web_sm` requires admin permissions on windows
* C++ Build tools are required on Windows for spaCy
* Pandoc is required for something on windows, but I can't remember what

## Windows Prerequisites

Install these on your windows machine before attempting the installation

[Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

[Pandoc - Universal Document Converter](https://pandoc.org/installing.html)

##Methods
### Windows - Manually
#### Step 1: Built-in Downloader

You need to get a copy of the requirements.txt provided with chatter, I recommend this method.

```
[p]repo add Fox https://github.com/bobloy/Fox-V3
```

#### Step 2: Install Requirements

In a terminal running as an admin, navigate to the directory containing this repo. 

I've used my install directory as an example.

```
cd C:\Users\Bobloy\AppData\Local\Red-DiscordBot\Red-DiscordBot\data\bobbot\cogs\RepoManager\repos\Fox\chatter
pip install -r requirements.txt
pip install --no-deps "chatterbot>=1.1"
```

#### Step 3: Load Chatter

```
[p]cog install Fox chatter
[p]load chatter
```

### Linux - Manually

Linux installation has not currently been evaluated, but Ubuntu testing is planned.

# Configuration

Chatter works out the the box without any training by learning as it goes, 
but will have very poor and repetitive responses at first.

Initial training is recommended to speed up its learning.

## Training Setup

### Minutes
```
[p]chatter minutes X
``` 
This command configures what Chatter considers the maximum amount of minutes 
that can pass between statements before considering it a new conversation.

Servers with lots of activity should set this low, where servers with low activity 
will want this number to be fairly high.

This is only used during training.

### Age

```
[p]chatter age X
``` 
This command configures the maximum number of days Chatter will look back when 
gathering messages for training.

Setting this to be extremely high is not recommended due to the increased disk space required to store
the data. Additionally, higher numbers will increase the training time tremendously.


## Training

### Train English

```
[p]chatter trainenglish
```

This will train chatter on basic english greetings and conversations. 
This is far from complete, but can act as a good base point for new installations.

### Train Channel

```
[p]chatter train #channel_name
``` 
This command trains Chatter on the specified channel based on the configured 
settings. This can take a long time to process.


## Switching Algorithms

```
[p]chatter algorithm X
```

Chatter can be configured to use one of three different Similarity algorithms.

Changing this can help if the response speed is too slow, but can reduce the accuracy of results.
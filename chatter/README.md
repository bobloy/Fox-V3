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

Chatter uses as sqlite database that can potentially take up a large amount of disk space,
depending on how much training Chatter has done. 

The sqlite database can be safely deleted at any time. Deletion will only erase training data.


# Installation
The installation is currently very tricky on Windows.

There are a number of reasons for this, but the main ones are as follows:
* Using a dev version of chatterbot
* Some chatterbot requirements conflict with Red's (as of 3.10)
* spaCy version is newer than chatterbot's requirements
* A symlink in spacy to map `en` to `en_core_web_sm` requires admin permissions on windows
* C++ Build tools are required on Windows for spaCy
* Pandoc is required for something on windows, but I can't remember what

Linux is a bit easier, but only tested on Debian and Ubuntu.

## Windows Prerequisites

**Requires 64 Bit Python to continue on Windows.**

Install these on your windows machine before attempting the installation:

[Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

[Pandoc - Universal Document Converter](https://pandoc.org/installing.html)

## Methods
### Automatic

This method requires some luck to pull off.

#### Step 1: Add repo and install cog

```
[p]repo add Fox https://github.com/bobloy/Fox-V3
[p]cog install Fox chatter
```

If you get an error at this step, stop and skip to one of the manual methods below.

#### Step 2: Install additional dependencies

Here you need to decide which training models you want to have available to you.

Shutdown the bot and run any number of these in the console:

```
python -m spacy download en_core_web_sm  # ~15 MB

python -m spacy download en_core_web_md  # ~50 MB

python -m spacy download en_core_web_lg  # ~750 MB (CPU Optimized)

python -m spacy download en_core_web_trf  # ~500 MB (GPU Optimized)
```

#### Step 3: Load the cog and get started

```
[p]load chatter
```

### Windows - Manually
Deprecated

### Linux - Manually
Deprecated

# Configuration

Chatter works out the box without any training by learning as it goes, 
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


### Train Ubuntu

```
[p]chatter trainubuntu
``` 
*WARNING:* This will trigger a large download and use a lot of processing power

This command trains Chatter on the publicly available Ubuntu Dialogue Corpus. (It'll talk like a geek)


## Switching Algorithms

```
[p]chatter algorithm X
```
or
```
[p]chatter algo X 0.95
```

Chatter can be configured to use one of three different Similarity algorithms.

Changing this can help if the response speed is too slow, but can reduce the accuracy of results.

The second argument is the maximum similarity threshold,
lowering that will make the bot stop searching sooner.

Default maximum similarity threshold is 0.90


## Switching Pretrained Models

```
[p]chatter model X
```

Chatter can be configured to use one of three pretrained statistical models for English.

I have not noticed any advantage to changing this, 
but supposedly it would help by splitting the search term into more useful parts.

See [here](https://spacy.io/models) for more info on spaCy models.

Before you're able to use the *large* model (option 3), you must install it through pip.

*Warning:* This is ~800MB download.

```
[p]pipinstall https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-2.3.1/en_core_web_lg-2.3.1.tar.gz#egg=en_core_web_lg
``` 

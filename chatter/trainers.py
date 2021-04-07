import asyncio
import csv
import html
import logging
import os
import pathlib
import time
from functools import partial

from chatterbot import utils
from chatterbot.conversation import Statement
from chatterbot.tagging import PosLemmaTagger
from chatterbot.trainers import Trainer
from redbot.core.bot import Red
from dateutil import parser as date_parser
from redbot.core.utils import AsyncIter

log = logging.getLogger("red.fox_v3.chatter.trainers")


class KaggleTrainer(Trainer):
    def __init__(self, chatbot, datapath: pathlib.Path, **kwargs):
        super().__init__(chatbot, **kwargs)

        self.data_directory = datapath / kwargs.get("downloadpath", "kaggle_download")

        self.kaggle_dataset = kwargs.get(
            "kaggle_dataset",
            "Cornell-University/movie-dialog-corpus",
        )

        # Create the data directory if it does not already exist
        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)

    def is_downloaded(self, file_path):
        """
        Check if the data file is already downloaded.
        """
        if os.path.exists(file_path):
            self.chatbot.logger.info("File is already downloaded")
            return True

        return False

    async def download(self, dataset):
        import kaggle  # This triggers the API token check

        future = await asyncio.get_event_loop().run_in_executor(
            None,
            partial(
                kaggle.api.dataset_download_files,
                dataset=dataset,
                path=self.data_directory,
                quiet=False,
                unzip=True,
            ),
        )

    def train(self, *args, **kwargs):
        log.error("See asynctrain instead")

    def asynctrain(self, *args, **kwargs):
        raise self.TrainerInitializationException()


class SouthParkTrainer(KaggleTrainer):
    def __init__(self, chatbot, datapath: pathlib.Path, **kwargs):
        super().__init__(
            chatbot,
            datapath,
            downloadpath="ubuntu_data_v2",
            kaggle_dataset="tovarischsukhov/southparklines",
            **kwargs,
        )


class MovieTrainer(KaggleTrainer):
    def __init__(self, chatbot, datapath: pathlib.Path, **kwargs):
        super().__init__(
            chatbot,
            datapath,
            downloadpath="kaggle_movies",
            kaggle_dataset="Cornell-University/movie-dialog-corpus",
            **kwargs,
        )

    async def run_movie_training(self):
        dialogue_file = "movie_lines.tsv"
        conversation_file = "movie_conversations.tsv"
        log.info(f"Beginning dialogue training on {dialogue_file}")
        start_time = time.time()

        tagger = PosLemmaTagger(language=self.chatbot.storage.tagger.language)

        # [lineID, characterID, movieID, character name, text of utterance]
        # File parsing from https://www.kaggle.com/mushaya/conversation-chatbot

        with open(self.data_directory / conversation_file, "r", encoding="utf-8-sig") as conv_tsv:
            conv_lines = conv_tsv.readlines()
        with open(self.data_directory / dialogue_file, "r", encoding="utf-8-sig") as lines_tsv:
            dialog_lines = lines_tsv.readlines()

        # trans_dict = str.maketrans({"<u>": "__", "</u>": "__", '""': '"'})

        lines_dict = {}
        for line in dialog_lines:
            _line = line[:-1].strip('"').split("\t")
            if len(_line) >= 5:  # Only good lines
                lines_dict[_line[0]] = (
                    html.unescape(("".join(_line[4:])).strip())
                    .replace("<u>", "__")
                    .replace("</u>", "__")
                    .replace('""', '"')
                )
            else:
                log.debug(f"Bad line {_line}")

        # collecting line ids for each conversation
        conv = []
        for line in conv_lines[:-1]:
            _line = line[:-1].split("\t")[-1][1:-1].replace("'", "").replace(" ", ",")
            conv.append(_line.split(","))

        # conversations = csv.reader(conv_tsv, delimiter="\t")
        #
        # reader = csv.reader(lines_tsv, delimiter="\t")
        #
        #
        #
        # lines_dict = {}
        # for row in reader:
        #     try:
        #         lines_dict[row[0].strip('"')] = row[4]
        #     except:
        #         log.exception(f"Bad line: {row}")
        #         pass
        #     else:
        #         # log.info(f"Good line: {row}")
        #         pass
        #
        # # lines_dict = {row[0].strip('"'): row[4] for row in reader_list}

        statements_from_file = []
        save_every = 300
        count = 0

        # [characterID of first, characterID of second, movieID, list of utterances]
        async for lines in AsyncIter(conv):
            previous_statement_text = None
            previous_statement_search_text = ""

            for line in lines:
                text = lines_dict[line]
                statement = Statement(
                    text=text,
                    in_response_to=previous_statement_text,
                    conversation="training",
                )

                for preprocessor in self.chatbot.preprocessors:
                    statement = preprocessor(statement)

                statement.search_text = tagger.get_text_index_string(statement.text)
                statement.search_in_response_to = previous_statement_search_text

                previous_statement_text = statement.text
                previous_statement_search_text = statement.search_text

                statements_from_file.append(statement)

            count += 1
            if count >= save_every:
                if statements_from_file:
                    self.chatbot.storage.create_many(statements_from_file)
                    statements_from_file = []
                count = 0

        if statements_from_file:
            self.chatbot.storage.create_many(statements_from_file)

        log.info(f"Training took {time.time() - start_time} seconds.")

    async def asynctrain(self, *args, **kwargs):
        extracted_lines = self.data_directory / "movie_lines.tsv"
        extracted_lines: pathlib.Path

        # Download and extract the Ubuntu dialog corpus if needed
        if not extracted_lines.exists():
            await self.download(self.kaggle_dataset)
        else:
            log.info("Movie dialog already downloaded")
        if not extracted_lines.exists():
            raise FileNotFoundError(f"{extracted_lines}")

        await self.run_movie_training()

        return True

        # train_dialogue = kwargs.get("train_dialogue", True)
        # train_196_dialogue = kwargs.get("train_196", False)
        # train_301_dialogue = kwargs.get("train_301", False)
        #
        # if train_dialogue:
        #     await self.run_dialogue_training(extracted_dir, "dialogueText.csv")
        #
        # if train_196_dialogue:
        #     await self.run_dialogue_training(extracted_dir, "dialogueText_196.csv")
        #
        # if train_301_dialogue:
        #     await self.run_dialogue_training(extracted_dir, "dialogueText_301.csv")


class UbuntuCorpusTrainer2(KaggleTrainer):
    def __init__(self, chatbot, datapath: pathlib.Path, **kwargs):
        super().__init__(
            chatbot,
            datapath,
            downloadpath="kaggle_ubuntu",
            kaggle_dataset="rtatman/ubuntu-dialogue-corpus",
            **kwargs,
        )

    async def asynctrain(self, *args, **kwargs):
        extracted_dir = self.data_directory / "Ubuntu-dialogue-corpus"

        # Download and extract the Ubuntu dialog corpus if needed
        if not extracted_dir.exists():
            await self.download(self.kaggle_dataset)
        else:
            log.info("Ubuntu dialogue already downloaded")
        if not extracted_dir.exists():
            raise FileNotFoundError("Did not extract in the expected way")

        train_dialogue = kwargs.get("train_dialogue", True)
        train_196_dialogue = kwargs.get("train_196", False)
        train_301_dialogue = kwargs.get("train_301", False)

        if train_dialogue:
            await self.run_dialogue_training(extracted_dir, "dialogueText.csv")

        if train_196_dialogue:
            await self.run_dialogue_training(extracted_dir, "dialogueText_196.csv")

        if train_301_dialogue:
            await self.run_dialogue_training(extracted_dir, "dialogueText_301.csv")

        return True

    async def run_dialogue_training(self, extracted_dir, dialogue_file):
        log.info(f"Beginning dialogue training on {dialogue_file}")
        start_time = time.time()

        tagger = PosLemmaTagger(language=self.chatbot.storage.tagger.language)

        with open(extracted_dir / dialogue_file, "r", encoding="utf-8") as dg:
            reader = csv.DictReader(dg)

            next(reader)  # Skip the header

            last_dialogue_id = None
            previous_statement_text = None
            previous_statement_search_text = ""
            statements_from_file = []

            save_every = 50
            count = 0

            async for row in AsyncIter(reader):
                dialogue_id = row["dialogueID"]
                if dialogue_id != last_dialogue_id:
                    previous_statement_text = None
                    previous_statement_search_text = ""
                    last_dialogue_id = dialogue_id
                    count += 1
                    if count >= save_every:
                        if statements_from_file:
                            self.chatbot.storage.create_many(statements_from_file)
                            statements_from_file = []
                        count = 0

                if len(row) > 0:
                    statement = Statement(
                        text=row["text"],
                        in_response_to=previous_statement_text,
                        conversation="training",
                        # created_at=date_parser.parse(row["date"]),
                        persona=row["from"],
                    )

                    for preprocessor in self.chatbot.preprocessors:
                        statement = preprocessor(statement)

                    statement.search_text = tagger.get_text_index_string(statement.text)
                    statement.search_in_response_to = previous_statement_search_text

                    previous_statement_text = statement.text
                    previous_statement_search_text = statement.search_text

                    statements_from_file.append(statement)

            if statements_from_file:
                self.chatbot.storage.create_many(statements_from_file)

        log.info(f"Training took {time.time() - start_time} seconds.")


class TwitterCorpusTrainer(Trainer):
    pass
    # def train(self, *args, **kwargs):
    #     """
    #     Train the chat bot based on the provided list of
    #     statements that represents a single conversation.
    #     """
    #     import twint
    #
    #     c = twint.Config()
    #     c.__dict__.update(kwargs)
    #     twint.run.Search(c)
    #
    #
    #     previous_statement_text = None
    #     previous_statement_search_text = ''
    #
    #     statements_to_create = []
    #
    #     for conversation_count, text in enumerate(conversation):
    #         if self.show_training_progress:
    #             utils.print_progress_bar(
    #                 'List Trainer',
    #                 conversation_count + 1, len(conversation)
    #             )
    #
    #         statement_search_text = self.chatbot.storage.tagger.get_text_index_string(text)
    #
    #         statement = self.get_preprocessed_statement(
    #             Statement(
    #                 text=text,
    #                 search_text=statement_search_text,
    #                 in_response_to=previous_statement_text,
    #                 search_in_response_to=previous_statement_search_text,
    #                 conversation='training'
    #             )
    #         )
    #
    #         previous_statement_text = statement.text
    #         previous_statement_search_text = statement_search_text
    #
    #         statements_to_create.append(statement)
    #
    #     self.chatbot.storage.create_many(statements_to_create)

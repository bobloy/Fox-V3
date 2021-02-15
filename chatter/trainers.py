import asyncio
import csv
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


class UbuntuCorpusTrainer2(KaggleTrainer):
    def __init__(self, chatbot, datapath: pathlib.Path, **kwargs):
        super().__init__(
            chatbot,
            datapath,
            downloadpath="ubuntu_data_v2",
            kaggle_dataset="rtatman/ubuntu-dialogue-corpus",
            **kwargs
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

            async for row in AsyncIter(reader):
                dialogue_id = row["dialogueID"]
                if dialogue_id != last_dialogue_id:
                    previous_statement_text = None
                    previous_statement_search_text = ""
                    last_dialogue_id = dialogue_id

                if len(row) > 0:
                    statement = Statement(
                        text=row["text"],
                        in_response_to=previous_statement_text,
                        conversation="training",
                        created_at=date_parser.parse(row["date"]),
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

        print("Training took", time.time() - start_time, "seconds.")

    def train(self, *args, **kwargs):
        log.error("See asynctrain instead")


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

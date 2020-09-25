from chatterbot import utils
from chatterbot.conversation import Statement
from chatterbot.trainers import Trainer


class TwitterCorpusTrainer(Trainer):
    def train(self, *args, **kwargs):
        """
        Train the chat bot based on the provided list of
        statements that represents a single conversation.
        """
        import twint

        c = twint.Config()
        c.__dict__.update(kwargs)
        twint.run.Search(c)


        previous_statement_text = None
        previous_statement_search_text = ''

        statements_to_create = []

        for conversation_count, text in enumerate(conversation):
            if self.show_training_progress:
                utils.print_progress_bar(
                    'List Trainer',
                    conversation_count + 1, len(conversation)
                )

            statement_search_text = self.chatbot.storage.tagger.get_text_index_string(text)

            statement = self.get_preprocessed_statement(
                Statement(
                    text=text,
                    search_text=statement_search_text,
                    in_response_to=previous_statement_text,
                    search_in_response_to=previous_statement_search_text,
                    conversation='training'
                )
            )

            previous_statement_text = statement.text
            previous_statement_search_text = statement_search_text

            statements_to_create.append(statement)

        self.chatbot.storage.create_many(statements_to_create)
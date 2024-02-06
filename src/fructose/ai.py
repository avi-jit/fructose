from functools import wraps
import inspect
import json
import os
import ast
from typing import Any, Type, TypeVar
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from fructose.type_parser import type_to_string, validate_return_type
from . import function_helpers
import openai

T = TypeVar('T')

LabeledArguments = dict[str, Any]

class Fructose():
    def __init__(self, client=None, model="gpt-4-turbo-preview"):
        if client is None:
            client = openai.Client(
                api_key=os.environ['OPENAI_API_KEY']
            )
        self._client = client
        self._model = model

    def _call_llm(self, messages: list[ChatCompletionMessageParam], debug: bool) -> str:
        if debug:
             for message in messages:
                if message['role'] == "system":
                    # print color: blue
                    print(f"\033[94mSystem: {message['content']}\033[0m")
                else:
                    # print color: green
                    print(f"\033[92mUser: {message['content']}\033[0m")

        chat_completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={
                "type":"json_object",
            },
        )

        result = chat_completion.choices[0].message.content
        if debug:
            print(result)


        if result is None:
            raise Exception("OpenAI chat completion failed")

        return result

    def _parse_llm_result(self, result: str, return_type: Type[T]) -> T:
        json_result = json.loads(result)

        # Very hacky but the logic is this:
        # The json.loads might in some cases do the correct type conversion, for example for bools it will
        res = json_result['the_actual_response_you_were_asked_for']

        # and for strings it does it as well, which is why we can early return 
        if return_type == str:
            return res
        
        # But in more complicated cases we "double check" it by converting it to a string and then using ast.literal_eval
        converted_value = ast.literal_eval(str(res))

        # and only then do the type casting
        typed_result = return_type(converted_value)

        # checks if the return type from the LLM is what the decorated function expects
        if type(typed_result) != return_type:
            raise ValueError(f"Type cast failed, value {typed_result} is of type {type(typed_result)}, expected {return_type}")

        return typed_result

    def _render_system(self, func_doc_string: str, return_type_str: str ) -> str:
        system = f"""
First figure out what steps you need to take to solve the problem defined by the following: 
\"{func_doc_string.strip()}. The return type should be {return_type_str}.\"
        
Then work through the problem. You can write code or pseudocode if necessary.

You may be given a set of arguments to work with.

Be concise and clear in your response.

Take a deep breath and work through it step by step.

Keep track of what was originally asked of you and make sure to actually answer correctly.

If you don't know, try anyway. Believe in yourself.""".strip()
        
        system_suffix = """
Answer with JSON in this format: 
{
    \"answer_format\": <what should the answer look like? \"single word\", \"list of words\", \"float\", etc>, 
    \"reasoning\": <your reasoning>, 
    \"answer_prep_steps\": [
        <step 1 in how you're preparing the answer>, 
        <step 2>, 
        ...
    ], 
    \"steps_applied\": [
        <step 1 applied to the given inputs>, 
        <step 2>, 
        ...
    ], 
    \"the_actual_response_you_were_asked_for\": <your final answer>
}
"""
        return f"{system}\n{system_suffix}".strip()

    def _render_prompt(self, labeled_arguments: dict[str, Any]) -> str:
        return f"{labeled_arguments}"


    def __call__(self, uses=None, debug=False):
        if uses is None:
            uses = []

        def decorator(func):
            return_annotation = inspect.signature(func).return_annotation
            validate_return_type(func.__name__, return_annotation)
            return_type_str = type_to_string(return_annotation)
            rendered_system = self._render_system(func.__doc__, return_type_str)

            @wraps(func)
            def wrapper(*args, **kwargs):
                labeled_arguments = function_helpers.collect_arguments(func, args, kwargs)
                rendered_prompt = self._render_prompt(labeled_arguments)

                messages = [
                    ChatCompletionSystemMessageParam(
                        role="system",
                        content=rendered_system
                    ),
                    ChatCompletionUserMessageParam(
                        role="user",
                        content=rendered_prompt
                    )
                ]
                raw_result = self._call_llm(messages, debug)
                result = self._parse_llm_result(raw_result, inspect.signature(func).return_annotation)

                return result

            return wrapper

        return decorator

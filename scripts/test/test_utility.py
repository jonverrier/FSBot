""" This script will take a list of questions and run them through the test pipeline."""

import logging
import os
import json
import openai
from openai.embeddings_utils import get_embedding
from tenacity import (
    retry,
    wait_random_exponential,
    stop_after_attempt,
    retry_if_not_exception_type,
)
from rich.progress import Progress
import numpy as np
from numpy.linalg import norm
from common.ApiConfiguration import ApiConfiguration

kOpenAiPersonaPrompt = "You are an AI assistant helping an application developer understand generative AI. You explain complex concepts in simple language, using Python examples if it helps. You limit replies to 50 words or less. If you don't know the answer, say 'I don't know'. If the question is not related to building AI applications, Python, or Large Language Models (LLMs), say 'That doesn't seem to be about AI'."
kInitialQuestionPrompt = "You are an AI assistant helping an application developer understand generative AI. You will be presented with a question. Answer the question in a few sentences, using language a suitable for a technical graduate student will understand. Limit your reply to 50 words or less. If you don't know the answer, say 'I don't know'. If the question is not related to building AI applications, Python, or Large Language Models (LLMs), say 'That doesn't seem to be about AI'.\n"
kEnrichmentPrompt = "You will be provided with a question about building applications that use generative AI technology. Write a 50 word summary of an article that would be a great answer to the question. Consider enriching the question with additional topics that the question asker might want to understand. Write the summary in the present tense, as though the article exists. If the question is not related to building AI applications, Python, or Large Language Models (LLMs), say 'That doesn't seem to be about AI'.\n"
kFollowUpPrompt = "You will be provided with a summary of an article about building applications that use generative AI technology. Write a question of no more than 10 words that a reader might ask as a follow up to reading the article."
kEnrichmentQuestionPrefix = "Question:"
kFollowUpPrefix = "Article summary: "

class test_result:
    def __init__(self) -> None:
        self.question = ""
        self.enriched_question = ""        
        self.hit = False 
        self.hitRelevance = 0
        self.hitSummary = ""
        self.followUp = ""
        self.followUpOnTopic = ""

    question: str
    enriched_question: str    
    hit: bool
    hitRelevance: float
    hitSummary: str
    followUp: str
    followUpOnTopic : str

@retry(
    wait=wait_random_exponential(min=5, max=15),
    stop=stop_after_attempt(15),
    retry=retry_if_not_exception_type(openai.InvalidRequestError),
)
def get_enriched_question(config: ApiConfiguration, text : str, logger):
    """generate a summary using chatgpt"""

    messages = [
        {
            "role": "system",
            "content": kOpenAiPersonaPrompt,
        },
        {
           "role": "user", 
           "content": kEnrichmentPrompt + kEnrichmentQuestionPrefix + text
        },
    ]

    response = openai.ChatCompletion.create(
        deployment_id=config.azureDeploymentName,
        model=config.modelName,
        messages=messages,
        temperature=0.7,
        max_tokens=config.maxTokens,
        top_p=0.0,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        request_timeout=config.openAiRequestTimeout,
    )

    text = response.get("choices", [])[0].get("message", {}).get("content", text)
    finish_reason = response.get("choices", [])[0].get("finish_reason", "")

    # print(finish_reason)
    if finish_reason != "stop" and finish_reason != 'length' and finish_reason != "":
        logger.warning("Stop reason: %s", finish_reason)
        logger.warning("Text: %s", text)
        logger.warning("Increase Max Tokens and try again")
        exit(1)

    return text


@retry(
    wait=wait_random_exponential(min=5, max=15),
    stop=stop_after_attempt(15),
    retry=retry_if_not_exception_type(openai.InvalidRequestError),
)
def get_text_embedding(config : ApiConfiguration, text: str, logger):
    """get the embedding for a text"""

    embedding = get_embedding(text, 
                              engine=config.azureEmbedDeploymentName, 
                              deployment_id=config.azureEmbedDeploymentName,
                              model=config.azureEmbedDeploymentName,
                              timeout=config.openAiRequestTimeout)
    return embedding


@retry(
    wait=wait_random_exponential(min=5, max=15),
    stop=stop_after_attempt(15),
    retry=retry_if_not_exception_type(openai.InvalidRequestError),
)
def get_followup_question(config: ApiConfiguration, text : str, logger):
    """generate a summary using chatgpt"""

    messages = [
        {
            "role": "system",
            "content": kFollowUpPrompt,
        },
        {
           "role": "user", 
           "content": text
        },
    ]

    response = openai.ChatCompletion.create(
        deployment_id=config.azureDeploymentName,
        model=config.modelName,
        messages=messages,
        temperature=0.7,
        max_tokens=config.maxTokens,
        top_p=0.0,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        request_timeout=config.openAiRequestTimeout,
    )

    text = response.get("choices", [])[0].get("message", {}).get("content", text)
    finish_reason = response.get("choices", [])[0].get("finish_reason", "")

    # print(finish_reason)
    if finish_reason != "stop" and finish_reason != 'length' and finish_reason != "":
        logger.warning("Stop reason: %s", finish_reason)
        logger.warning("Text: %s", text)
        logger.warning("Increase Max Tokens and try again")
        exit(1)

    return text

@retry(
    wait=wait_random_exponential(min=5, max=15),
    stop=stop_after_attempt(15),
    retry=retry_if_not_exception_type(openai.InvalidRequestError),
)
def assess_followup_question(config: ApiConfiguration, text : str, logger):
    """generate a summary using chatgpt"""

    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant helping a team of developers understand AI. You explain complex concepts in simple language. You will be asked a question. Respond 'yes' if the question appears to be about AI, otherwise respond 'no'."
        },
        {
           "role": "user", 
           "content": text
        },
    ]

    response = openai.ChatCompletion.create(
        deployment_id=config.azureDeploymentName,
        model=config.modelName,
        messages=messages,
        temperature=0.7,
        max_tokens=config.maxTokens,
        top_p=0.0,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        request_timeout=config.openAiRequestTimeout,
    )

    text = response.get("choices", [])[0].get("message", {}).get("content", text)
    finish_reason = response.get("choices", [])[0].get("finish_reason", "")

    # print(finish_reason)
    if finish_reason != "stop" and finish_reason != 'length' and finish_reason != "":
        logger.warning("Stop reason: %s", finish_reason)
        logger.warning("Text: %s", text)
        logger.warning("Increase Max Tokens and try again")
        exit(1)

    return text

def cosine_similarity(a, b): 
   result = np.dot(a, b) / (norm(a) * norm(b))
   return result


def run_tests(config, testDestinationDir, sourceDir, questions): 

   logging.basicConfig(level=logging.WARNING)
   logger = logging.getLogger(__name__)

   openai.api_type = config.apiType 
   openai.api_key = config.apiKey
   openai.api_base = config.resourceEndpoint
   openai.api_version = config.apiVersion 
   
   if not testDestinationDir:
      logger.error("Test data folder not provided")
      exit(1)

   results = []

   # load the existing chunks from a json file
   cache_file = os.path.join(sourceDir, "embeddings_lite.json")
   if os.path.isfile(cache_file):
      with open(cache_file, "r", encoding="utf-8") as f:
         current = json.load(f)       

   logger.info("Starting test run, total questions to be processed: %s", len(questions))

   for question in questions:
      result = test_result()
      result.question = question

      result.enriched_qustion = get_enriched_question (config, question, logger)

      # Convert the text of the enriched question to a vector embedding
      embedding = get_text_embedding(config, result.enriched_qustion, logger)
   
      # Iterate through the chunks we have stored 
      for chunk in current:
         
         # calculate the similarity between the chunk and the question
         ada = chunk.get ("ada_v2")
         similarity = cosine_similarity (ada, embedding)

         # If we pass a reasonableness threshold, count it as a hit
         if similarity > 0.8:
            result.hit = True
         
         # If it is the best hit so far, record the match
         if similarity > result.hitRelevance:
            result.hitRelevance = similarity 
            result.hitSummary = chunk.get("summary")

      # Ask GPT for a follow up question on the best match
      # Once we have a follow up, ask GPT if the follow up looks like it is about AI            
      result.followUp = get_followup_question (config, result.hitSummary, logger)
      result.followUpOnTopic = assess_followup_question (config, result.followUp, logger)            

      results.append (result)

   logger.debug("Total tests processed: %s", len(results))

   output_results = []
   for result in results:
      output = dict()
      output["question"] = result.question
      output["enriched_question"] = result.enriched_qustion
      output["hit"] = result.hit   
      output["summary"] = result.hitSummary        
      output["hitRelevance"] = result.hitRelevance      
      output["followUp"] = result.followUp  
      output["followUpOnTopic"] = result.followUpOnTopic             
      output_results.append (output)
      
   # save the test results to a json file
   output_file = os.path.join(testDestinationDir, "test_output.json")
   with open(output_file, "w", encoding="utf-8") as f:
      json.dump(output_results, f)

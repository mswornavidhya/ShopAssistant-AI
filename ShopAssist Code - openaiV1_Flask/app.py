from flask import Flask, redirect, url_for, render_template, request
from functions import initialize_conversation, initialize_conv_reco, get_chat_model_completions, moderation_check,intent_confirmation_layer,dictionary_present,compare_laptops_with_user,recommendation_validation

import openai
import ast
import re
import pandas as pd
import json

# read the API key
openai.api_key = open("openaikey.txt", "r").read().strip()

app = Flask(__name__)

conversation_bot = []
conversation = initialize_conversation()
introduction = get_chat_model_completions(conversation)
conversation_bot.append({'bot':introduction})
top_3_laptops = None

@app.route("/")
def default_func():
    global conversation_bot, conversation, top_3_laptops
    return render_template("index_bot.html", name_xyz = conversation_bot)

@app.route("/end_conv", methods = ['POST','GET'])
def end_conv():
    global conversation_bot, conversation, top_3_laptops
    conversation_bot = []
    conversation = initialize_conversation()
    introduction = get_chat_model_completions(conversation)
    conversation_bot.append({'bot':introduction})
    top_3_laptops = None
    return redirect(url_for('default_func'))

@app.route("/invite", methods = ['POST'])
def invite():
    global conversation_bot, conversation, top_3_laptops, conversation_reco
    user_input = request.form["user_input_message"]
    print('Inside Invite: \n',user_input,'\n')
    prompt = 'Remember your system message and that you are an intelligent laptop assistant. So, you only help with questions around laptop.'
    moderation = moderation_check(user_input)
    if moderation == 'Flagged':
        return redirect(url_for('end_conv'))

    if top_3_laptops is None:

        conversation.append({"role": "user", "content": user_input + '. ' + prompt})
        conversation_bot.append({'user':user_input})
        print('top_3_laptops is None\n conversation :',conversation,'\n')

        response_assistant = get_chat_model_completions(conversation)
        print('top_3_laptops is None\nresponse_assistant : ',response_assistant,'\n')
        
        moderation = moderation_check(response_assistant)
        if moderation == 'Flagged':
            return redirect(url_for('end_conv'))

        confirmation = intent_confirmation_layer('assistant', response_assistant)
        print(f"confirmation = intent_confirmation_layer('assistant', response_assistant) \n confirmation : {confirmation}")

        moderation = moderation_check(confirmation)        
        if moderation == 'Flagged':
            return redirect(url_for('end_conv'))

        if "No" in confirmation:
            conversation.append({"role": "assistant", "content": response_assistant})
            conversation_bot.append({'bot':response_assistant})
        else:
            response = dictionary_present('assistant', response_assistant)

            moderation = moderation_check(response)
            if moderation == 'Flagged':
                return redirect(url_for('end_conv'))

            conversation_bot.append({'bot':"Thank you for providing all the information. Kindly wait, while I fetch the products: \n"})
             
            if response_assistant.get("function_call"):
                function_args = json.loads(response["function_call"]["arguments"])                
                top_3_laptops = compare_laptops_with_user(function_args)
            else:
                top_3_laptops = compare_laptops_with_user(response)

            validated_reco = recommendation_validation(top_3_laptops)

            if len(validated_reco) == 0:
                conversation_bot.append({'bot':"Sorry, we do not have laptops that match your requirements. Connecting you to a human expert. Please end this conversation."})

            conversation_reco = initialize_conv_reco(validated_reco) 

            if response.get("function_call"):
                print(' \n*******\n\nBEGIN Function CALL \n*******\n\n')
                function_name = response["function_call"]["name"]
                conversation_reco.append(response_assistant)
                conversation_reco.append(
                    {
                        "role": "function",
                        "name": function_name,
                        "content": validated_reco,
                    }
                )
                print(' \n*******\n\nEND OF Inside Function CALL \n*******\n\n')

            recommendation = get_chat_model_completions(conversation_reco)

            moderation = moderation_check(recommendation)        
            if moderation == 'Flagged':
                return redirect(url_for('end_conv'))

            conversation_reco.append({"role": "user", "content": "This is my user profile" + response})

            conversation_reco.append({"role": "assistant", "content": recommendation})
            conversation_bot.append({'bot':recommendation})

            print(recommendation + '\n')

    else:
        print('Top 3 laptops found\n')
        conversation_reco.append({"role": "user", "content": user_input})
        conversation_bot.append({'user':user_input})

        print('AFter Recommendation - provided, \nConversation_reco:',conversation_reco)

        response_asst_reco = get_chat_model_completions(conversation_reco)
        print('response_asst_reco:',response_asst_reco)

        moderation = moderation_check(response_asst_reco)       
        if moderation == 'Flagged':
            return redirect(url_for('end_conv'))

        conversation.append({"role": "assistant", "content": response_asst_reco})
        conversation_bot.append({'bot':response_asst_reco})

    return redirect(url_for('default_func'))

if __name__ == '__main__':
    app.run(debug=True, host= "0.0.0.0")
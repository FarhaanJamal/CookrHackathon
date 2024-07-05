import pandas as pd
from collections import Counter
import google.generativeai as genai
from dotenv import load_dotenv
import os
import PIL.Image
import csv
load_dotenv()

genai.configure(api_key=os.getenv('API_KEY'))

def cusineEvaluator(cusineLst, dishes):
    ans = ""
    countDct = Counter(cusineLst)
    #print(countDct)
    for key, val in countDct.items():
        if val == 1:
            ind = cusineLst.index(key)
            ans = ["Rejected", f"the Cusine of {dishes[ind]} does not match with rest of the dishes"]
            return ans
        if val <= len(dishes)/3:
            ind = cusineLst.index(key)
            ans = ["Manual", f"the Cusine of {dishes[ind]} does not match with rest of the dishes"]
            return ans
    ans = ["Accepted", "the Cusine of all dishes are matching"]
    return ans

def vegEvaluator(vegLst, dishes):
    ans = ""
    countDct = Counter(vegLst)
    #print(countDct)
    for key, val in countDct.items():
        if val == 1:
            ind = vegLst.index(key)
            ans = ["rejected", f"this {dishes[ind]} is {key} and not matching with rest of the dishes"]
            return ans
        if val <= len(dishes)/3:
            ind = vegLst.index(key)
            ans = ["manual", f"this {dishes[ind]} is {key} and not matching with rest of the dishes"]
            return ans
    ans = ["accepted", "the veg of all dishes are matching"]
    return ans

def priceEvaluator(convo, prices, dishes):
    ans = ""
    for i in range(len(dishes)):
        convo.send_message(f"Is {prices[i]} rupees for the dish: {dishes[i]} is (cheap, normal, overpriced)\n to accept or reject the dish with a valid reason\n scale your confidence about your decision between 1 to 100\nNote:ouput should be in the format - \"confidence points, accepted/rejected, reason\"")
        pricing = convo.last.text
        pricing = pricing.split(",")
        #print(pricing)
        if int(pricing[0]) >= 75:
            ans = pricing[1:]
            if ans[0].lower() == "rejected":
                return ans
        else:
            ans = ["manual", pricing[2]]
            return ans
    ans = ["accepted", "the dishes are correctly priced"]
    return ans

def ingEvaluate(res):
    res = res.split(",")
    if int(res[0]) >= 85:
        ans = res[1:]
        if ans[0].lower() == "rejected":
            return ans
        else:
            ans = ["manual", res[2]]
            return ans
    ans = ["accepted", "the dishes are correctly priced"]
    return ans

def imgAndQualityEvaluator(dataNewMenu, imgModel, convo, dishes):
    ans = ""
    for index, row in dataNewMenu.iterrows():
        img = PIL.Image.open(row["Image"])
        imgMistakeResponse = imgModel.generate_content([f"what is the dish in the image\n scale your confidence about your dish identification between 1 to 100\nNote:ouput should be in the format - \"<confidence points>,<dish_name>", img])
        imgDish = imgMistakeResponse.text
        imgDish = imgDish.split(",")
        #print(imgDish)
        convo.send_message(f"Is {imgDish[1]} and {dishes[index]} same?\n to accept or reject the dish with a valid reason if they are same\n scale your confidence about your decision between 1 to 100\nNote:ouput should be in the format - \"<confidence points>, accepted/rejected, <dish and the image are same>/mistake reason\"")
        imgDishMistake = convo.last.text
        imgDishMistake = imgDishMistake.split(",")
        #print(imgDishMistake)
        if int(imgDishMistake[0]) >= 90:
            ans = imgDishMistake[1:]
            if ans[0].lower() == "rejected":
                return ans
        else:
            ans = ["manual", f"Dish: {dishes[index]} : Image Mismatch : {imgDishMistake[2]}"]
            return ans
        qualityResponse = imgModel.generate_content([f"Based on the visual cues analyze the given image for hygiene, color, texture and consistency.\n to accept or reject the dish with a valid reason\n scale your confidence about your dish identification between 1 to 100\nNote:ouput should be in the format- \"<confidence points>, accepted/rejected, <no image mistakes found>/mistake reason", img])
        quality = qualityResponse.text
        quality = quality.split(",")
        #print(quality)
        if int(quality[0]) >= 90:
            ans = quality[1:]
            if ans[0].lower() == "rejected":
                return ans
        else:
            ans = ["manual", f"Dish: {dishes[index]} : Food Quality Remark : {quality[2]}"]
            return ans
    ans = ["accepted", "the dishes and the image provided are same and the quality of food is good"]
    return ans


def item_check_alldish(item):
    all_dishes_pd = pd.read_csv(os.path.join("db", "all_dishs.csv"))
    all_dishes_dict = all_dishes_pd.to_dict(orient="records")
    searchkey = item[0]
    for i in all_dishes_dict:
        if i["Name"] == searchkey:
            return i["Ingredients"]


"""item = [
    "Pongal",
    "./Imags/chapathi.png",
    "Rice, Moong dal, Black pepper, Cumin seeds, Ginger, Ghee, Cashew nuts",
    "30",
]
fileloc = "/Users/raghav/Documents/programs/2024/cookr_hackathon/latest/database/all_dishs.csv"


print(item_check_alldish(item, fileloc))"""

def menuReviewer(kitchenName, extraDishesLoc, oldMenuLoc="Empty"):
    newMenuLoc = None
    generation_config = {"temperature": 0.9, "top_p": 1, "top_k": 1, "max_output_tokens": 2048}

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
    ]

    txtModel = genai.GenerativeModel(model_name="gemini-1.0-pro",
    generation_config=generation_config,
    safety_settings=safety_settings)

    imgModel = genai.GenerativeModel("gemini-pro-vision")

    if oldMenuLoc == "Empty":
        newMenuLoc = extraDishesLoc
        dataNewMenu = pd.read_csv(newMenuLoc)
        #print(dataNewMenu.head())

        dishes = dataNewMenu.iloc[:, 0].to_numpy()
        prices = dataNewMenu.iloc[:, -1].to_numpy()
        menu = ""
        for index, row in dataNewMenu.iterrows():
            ingred = row['Ingredients'].replace(",", "-")
            menu += f"{row['Name']}-{row['Image']}-{ingred}-{row['Price']}_"
        menu = menu[:-1]
        #print(menu)

        convo = txtModel.start_chat(history=[])
        convo.send_message(f"Identify any spelling mistakes in the menu: {dataNewMenu}\n to accept or reject the menu with a valid reason\nNote:ouput should be in the format - \"accepted/rejected,no spelling mistakes found/spelling mistake found in dish_name: \"mistake\" should be \"correct spelling\"\"")
        spelling = convo.last.text
        spelling = spelling.split(",")
        #print(spelling)
        spellingResult, spellingRemark = spelling[0], spelling[1]
        #print(spellingResult)
        if spellingResult.lower() == "rejected":
            return [spellingResult, spellingRemark]
        
        convo = txtModel.start_chat(history=[])
        cusineLst = []
        vegLst = []
        for index, row in dataNewMenu.iterrows():
            convo.send_message(f"Identify the cusine of the dish: {row['Name']}\nNote:ouput should be in one format - \"cusine\"")
            cusine = convo.last.text
            cusineLst.append(cusine)
            #print(cusine)
            convo.send_message(f"Identify the whether the dish: {row['Name']} is vegetarian or not with respect to the ingredients: {row['Ingredients']}\nNote:ouput should be in one format - \"veg/non-veg\"")
            veg = convo.last.text
            vegLst.append(veg)
            #print(veg)
            ing = (item_check_alldish(row))
            convo.send_message(f"Is both {ing} and {row['Ingredients']} are same\n to accept or reject the dish with a valid reason\n scale your confidence about your decision between 1 to 100\nNote:ouput should be in the format - \"confidence points, accepted/rejected, reason\"")
            res = convo.last.text
            ans = ingEvaluate(res)
            #print(ans)
            if ans[0].lower() == "rejected":
                return [ans[0], ans[1]]
            if ans[0].lower() == "manual":
                return [ans[0], ans[1]]
            

        ans = cusineEvaluator(cusineLst, dishes)
        #print(ans)
        if ans[0].lower() == "rejected":
            return [ans[0], ans[1]]
        if ans[0].lower() == "manual":
            return [ans[0], ans[1]]
        
        ans = vegEvaluator(vegLst, dishes)
        #print(ans)
        if ans[0].lower() == "rejected":
            return [ans[0], ans[1]]
        if ans[0].lower() == "manual":
            return [ans[0], ans[1]]

        ans = priceEvaluator(convo, prices, dishes)
        #print(ans)
        if ans[0].lower() == "rejected":
            return [ans[0], ans[1]]
        if ans[0].lower() == "manual":
            return [ans[0], ans[1]]
        

        ans = imgAndQualityEvaluator(dataNewMenu, imgModel, convo, dishes)
        #print(ans)
        if ans[0].lower() == "rejected":
            return [ans[0], ans[1]]
        if ans[0].lower() == "manual":
            return [ans[0], ans[1]]
        
    if oldMenuLoc != "Empty":
        dataNewMenu = pd.read_csv(extraDishesLoc)
        dataOldMenu = pd.read_csv(oldMenuLoc)
        #print(dataNewMenu.head())

        dishes = dataNewMenu.iloc[:, 0].to_numpy()
        prices = dataNewMenu.iloc[:, -1].to_numpy()
        menu = ""
        for index, row in dataNewMenu.iterrows():
            ingred = row['Ingredients'].replace(",", "-")
            menu += f"{row['Name']}-{row['Image']}-{ingred}-{row['Price']}_"
        menu = menu[:-1]
        #print(menu)

        convo = txtModel.start_chat(history=[])
        convo.send_message(f"Identify any spelling mistakes in the menu: {dataNewMenu}\n to accept or reject the menu with a valid reason\nNote:ouput should be in the format - \"accepted/rejected,no spelling mistakes found/spelling mistake found in dish_name: \"mistake\" should be \"correct spelling\"\"")
        spelling = convo.last.text
        spelling = spelling.split(",")
        #print(spelling)
        spellingResult, spellingRemark = spelling[0], spelling[1]
        #print(spellingResult)
        if spellingResult.lower() == "rejected":
            return [spellingResult, spellingRemark]
        
        convo = txtModel.start_chat(history=[])
        cusineLst = []
        vegLst = []
        dataFullMenu = pd.read_csv(oldMenuLoc)
        for index, row in dataNewMenu.iterrows():
            dataFullMenu.loc[len(dataFullMenu.index)] = row
        fullDishes = dataNewMenu.iloc[:, 0].to_numpy()
        for index, row in dataFullMenu.iterrows():
            convo.send_message(f"Identify the cusine of the dish: {row['Name']}\nNote:ouput should be in one format - \"cusine\"")
            cusine = convo.last.text
            cusineLst.append(cusine)
            #print(cusine)
            convo.send_message(f"Identify the whether the dish: {row['Name']} is vegetarian or not with respect to the ingredients: {row['Ingredients']}\nNote:ouput should be in one format - \"veg/non-veg\"")
            veg = convo.last.text
            vegLst.append(veg)
            #print(veg)
            ing = (item_check_alldish(row))
            convo.send_message(f"Is both {ing} and {row['Ingredients']} are same\n to accept or reject the dish with a valid reason\n scale your confidence about your decision between 1 to 100\nNote:ouput should be in the format - \"confidence points, accepted/rejected, reason\"")
            res = convo.last.text
            ans = ingEvaluate(res)
            #print(ans)
            if ans[0].lower() == "rejected":
                return [ans[0], ans[1]]
            if ans[0].lower() == "manual":
                return [ans[0], ans[1]]

        ans = cusineEvaluator(cusineLst, fullDishes)
        #print(ans)
        if ans[0].lower() == "rejected":
            return [ans[0], ans[1]]
        if ans[0].lower() == "manual":
            return [ans[0], ans[1]]
        
        ans = vegEvaluator(vegLst, fullDishes)
        #print(ans)
        if ans[0].lower() == "rejected":
            return [ans[0], ans[1]]
        if ans[0].lower() == "manual":
            return [ans[0], ans[1]]

        ans = priceEvaluator(convo, prices, dishes)
        #print(ans)
        if ans[0].lower() == "rejected":
            return [ans[0], ans[1]]
        if ans[0].lower() == "manual":
            return [ans[0], ans[1]]
        

        ans = imgAndQualityEvaluator(dataNewMenu, imgModel, convo, dishes)
        #print(ans)
        if ans[0].lower() == "rejected":
            return [ans[0], ans[1]]
        if ans[0].lower() == "manual":
            return [ans[0], ans[1]]
    return ["Accepted", "EveryThing is fine"]
        
res = menuReviewer("Vijay kitchen", os.path.join("media", "menu1.csv"))
#res = menuReviewer("Vijay kitchen", os.path.join("media", "menu1.csv"), os.path.join("media", "dish2.csv"))
print(res[0], res[1])


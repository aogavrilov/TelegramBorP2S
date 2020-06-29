import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, executor, types
from PIL import Image
import os
import sklearn
import sklearn.preprocessing
from aiogram.types import ChatActions

from styletr import StyleTransfer

tgTok = None
deepmxTok = None
import numpy as np


import deepmux
from torchvision import transforms
#logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
with open("config.json", "r") as readcfg:
    data = json.load(readcfg)
    tgTok = data['tgTok']
    deepmxTok = data['deepmxTok']
tgTok = '1159135693:AAFf_A3pLRsBfdkVVzRYRMbVeVEvzE-RFjQ'
bot = Bot(token=tgTok)
disp = Dispatcher(bot)


styles = set()
cycle = set()
styles_ = set()


class SomeModel:
    def __init__(self, model_name):
        # Создаем модель в DeepMux
        self.model = deepmux.get_model(model_name=model_name, token=deepmxTok)

        self._imagenet_mean = [0.5, 0.5, 0.5]
        self._imagenet_std = [0.5, 0.5, 0.5]

    def __call__(self, image: Image) -> np.ndarray:
        input_batch = self._preprocess_image(image)
        model_outputs = self.model.run(input_batch)
        category_probs = model_outputs[0]
        init_shape = category_probs.shape
        category_probs = sklearn.preprocessing.MinMaxScaler() \
            .fit_transform(np.ravel(category_probs)[:, None]) \
            .reshape(init_shape)
        return category_probs

    def _preprocess_image(self, image) -> np.ndarray:
        preprocess = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=self._imagenet_mean,
                                 std=self._imagenet_std),
        ])
        input_tensor = preprocess(image)
        input_batch = input_tensor.unsqueeze(0)
        return input_batch.numpy()

model = SomeModel("P2S")


@disp.message_handler(commands="start")
async def start_dialog(message: types.Message):
    poll_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    poll_keyboard.add(types.KeyboardButton("О приложении"))
    poll_keyboard.add(types.KeyboardButton("Style Transfer"))
    poll_keyboard.add(types.KeyboardButton("Преобразовать фото в скетч(криво увы)"))
    # poll_keyboard.add(types.KeyboardButton("Поддержать"))
    poll_keyboard.add(types.KeyboardButton("Отмена"))
    await message.answer("Выберите действие, которое хотите совершить", reply_markup=poll_keyboard)

@disp.message_handler(commands="log")
async def return_log(message: types.Message):
    user_id = message.from_user.id
    await bot.send_chat_action(user_id, ChatActions.UPLOAD_DOCUMENT)
    await asyncio.sleep(1)  # скачиваем файл и отправляем его пользователю
    TEXT_FILE = open("app.log", "rb")
    await bot.send_document(user_id, TEXT_FILE)

@disp.message_handler()
async def echo(message: types.Message):
    if (message.text == "О приложении"):
        await message.answer("Данное приложение делает из фото скетч, применяя технологию cycleGAN. \nКогда вы нажмете "
                             "кнопку ''Преобразовать фото в скетч'' вы получите инструкции для этого преобразования\n"
                             "Построение изображения может занять пару секунд. Когда приложение завершит свою работу, "
                             "оно пришлет вам результат. \nДанное приложение создано в рамках выпускного проекта DLS.\n"
                             "Пример работы программы вы можете видеть ниже:")
    elif (message.text == "Преобразовать фото в скетч(криво увы)"):
        if(message.from_user.id in styles_):
            styles_.remove(message.from_user.id)
        if(message.from_user.id in styles):
            styles.remove(message.from_user.id)
        await message.answer("Отправьте ОДНО фото, которое хотите преобразовать в скетч")
        cycle.add(message.from_user.id)

    elif(message.text == "Style Transfer"):
        if(message.from_user.id in cycle):
            cycle.remove(message.from_user.id)
        await message.answer("Отправьте ОДНО фото, на которое хотите наложить стиль")
        styles.add(message.from_user.id)

    elif (message.text == "Отмена"):
        tmp = types.ReplyKeyboardRemove()
        await message.answer(
            "Спасибо, что воспользовались нашим приложением. Вы всегда можете ввести /start и продолжить развлекаться.",
            reply_markup=tmp)
        if (message.from_user.id in styles_):
            styles_.remove(message.from_user.id)
        if (message.from_user.id in styles):
            styles.remove(message.from_user.id)
        if (message.from_user.id in cycle):
            cycle.remove(message.from_user.id)

    else:
        await message.answer("Данная команда неизвестна. Введите /start для отображения меню.")
        print(message.text)


@disp.message_handler(content_types=["photo"])
async def photo_ed(message: types.Message):
    if(message.from_user.id in cycle):

        await message.photo[-1].download("images/" + str(message.from_user.id) + '.jpg')
        img = Image.open('images/'+ str(message.from_user.id) + '.jpg')
        #open("images/" + str(message.from_user.id) + '.jpg', 'rb')
        h, w = img.size
        # print(img.shape)
        t1 = transforms.Compose([
            transforms.Resize((512, 512)),
          #  transforms.ToTensor()
        ])
        img = t1(img)
        img = model(img)
        img = np.transpose(img, (1, 2, 0))
        img = Image.fromarray((img * 255).astype(np.uint8))
        t = transforms.Compose([
            transforms.Resize((w, h)),
            transforms.ToTensor()
        ])
        img = t(img).numpy()
        img = np.transpose(img, (1, 2, 0))
        img = Image.fromarray(np.uint8(img * 255))
        img.save('images/'+ str(message.from_user.id) + '.jpg')
        img_ = open('images/'+ str(message.from_user.id) + '.jpg', 'rb')
        await bot.send_photo(message.from_user.id, img_, caption="Преобразованное фото")
        cycle.remove(message.from_user.id)
        os.remove("images/" + str(message.from_user.id) + '.jpg')
    elif(message.from_user.id in styles):
        await message.photo[-1].download("images/" + str(message.from_user.id) + '.jpg')
        styles.remove(message.from_user.id)
        styles_.add(message.from_user.id)
        await message.answer("Принято! Отправь еще фотку стиля, который нужно перенести.")
    elif(message.from_user.id in styles_):
        await message.photo[-1].download("images/" + str(message.from_user.id) + 'style.jpg')
        #img = Image.open('images/' + str(message.from_user.id) + '.jpg')
        await message.answer("Отлично! Осталось подождать 5-10 минут и бот пришлет результат.")
        nm = StyleTransfer("images/" + str(message.from_user.id) + '.jpg', "images/" + str(message.from_user.id) + 'style.jpg')
        x = await nm.getRes()

        x = Image.fromarray((x.detach().numpy().squeeze(0).transpose((1, 2, 0)) * 255).astype(np.uint8))
        x.save("images/" + str(message.from_user.id) + '.jpg')
        img_ = open('images/' + str(message.from_user.id) + '.jpg', 'rb')
        await bot.send_photo(message.from_user.id, img_, caption="Преобразованное фото")
        styles_.remove(message.from_user.id)
        os.remove("images/" + str(message.from_user.id) + '.jpg')
        os.remove( "images/" + str(message.from_user.id) + 'style.jpg')
    else:
        await message.answer("Ой, ты не выбрал, что хочешь сделать с картинкой. Введи /start и выбери на клавиатуре действие!")





if __name__ == "__main__":
    executor.start_polling(disp, skip_updates=True)

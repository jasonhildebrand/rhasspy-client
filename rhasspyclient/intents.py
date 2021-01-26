import asyncio
import websockets
import json
from urllib.parse import urljoin


def is_intent(func):
    func.is_intent = True
    return func


class IntentAction(object):

    def intents(self):
        """
        Returns all methods in current class which
        are decorated using is_intent().
        """
        for method in self.__class__.__dict__.values():
            if hasattr(method, 'is_intent'):
                yield (method.__name__, getattr(self, method.__name__))


class IntentHandler(object):

    def __init__(self, client):
        self.client = client
        self.intent_resolver = {}
        self.action_for_intent = {}

    def add_intent_action(self, action):
        for name, method in action.intents():
            self.intent_resolver[name] = method
            self.action_for_intent[name] = action

    def resolve(self, intent_name):
        return self.intent_resolver.get(intent_name)

    async def get_event(self):
        url = urljoin(self.client.api_url, 'events/intent').replace('https', 'ws').replace('http', 'ws')
        global timers
        async with websockets.connect(url) as websocket:
            intent = await websocket.recv()
            intent = json.loads(intent)
            print(f"< {intent}")
            cmd = (intent['intent']['name'])
            i = self.resolve(cmd)
            if i:
                await i(intent, self.client)
            else:
                print('Got unhandled command: %s' % cmd)

    async def set_sentences(self):
        s = {}
        for intent, method in self.intent_resolver.items():
            action = self.action_for_intent[intent]
            if hasattr(action, 'get_sentences'):
                s[intent] = action.get_sentences(intent)
            else:
                s[intent] = [l.strip() for l in method.__doc__.strip().split("\n")]
            print(intent, s[intent])
        await self.client.set_sentences(s)

    def train(self):
        async def do_train():
            await self.set_sentences()
            await self.client.train()
        asyncio.get_event_loop().run_until_complete(do_train())

    def run(self):
        while True:
            asyncio.get_event_loop().run_until_complete(self.get_event())

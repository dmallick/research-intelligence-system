# Test that everything works together

import openai
import langchain
import langchain_openai
from langchain_openai import ChatOpenAI
print('✅ All AI packages working together!')
print(f'OpenAI version: {openai.__version__}')
print(f'LangChain version: {langchain.__version__}')
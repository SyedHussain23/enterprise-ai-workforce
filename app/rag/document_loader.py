import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter


def load_documents():

    documents = []

    base_path = "data"

    if not os.path.exists(base_path):
        print("❌ Data folder not found")
        return []

    for category in os.listdir(base_path):

        category_path = os.path.join(base_path, category)

        if os.path.isdir(category_path):

            for file in os.listdir(category_path):

                if file.endswith(".txt"):

                    file_path = os.path.join(category_path, file)

                    loader = TextLoader(file_path)
                    docs = loader.load()

                    # ✅ ADD SOURCE METADATA (CRITICAL)
                    for doc in docs:
                        doc.metadata["source"] = file
                        doc.metadata["category"] = category

                    documents.extend(docs)

    splitter = CharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_documents(documents)

    print(f"✅ Loaded {len(chunks)} chunks")

    return chunks
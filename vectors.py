import os
import base64
import pandas as pd
from markitdown import MarkItDown
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.schema import Document
from typing import List, Dict, Any


class EmbeddingsManager:
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en",
        device: str = "cpu",
        encode_kwargs: dict = {"normalize_embeddings": True},
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "vector_db",
    ):
        """
        Initializes the EmbeddingsManager with the specified model and Qdrant settings.

        Args:
            model_name (str): The HuggingFace model name for embeddings.
            device (str): The device to run the model on ('cpu' or 'cuda').
            encode_kwargs (dict): Additional keyword arguments for encoding.
            qdrant_url (str): The URL for the Qdrant instance.
            collection_name (str): The name of the Qdrant collection.
        """
        self.model_name = model_name
        self.device = device
        self.encode_kwargs = encode_kwargs
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name

        self.embeddings = HuggingFaceBgeEmbeddings(
            model_name=self.model_name,
            model_kwargs={"device": self.device},
            encode_kwargs=self.encode_kwargs,
        )

        # Initialize MarkItDown for PowerPoint processing
        self.markitdown = MarkItDown()

    def _process_excel_file(self, file_path: str) -> List[Document]:
        """
        Process Excel files and convert them to Document objects.
        
        Args:
            file_path (str): Path to the Excel file
            
        Returns:
            List[Document]: List of Document objects containing Excel data
        """
        documents = []
        
        try:
            # Read all sheets from the Excel file
            excel_file = pd.ExcelFile(file_path)
            
            for sheet_name in excel_file.sheet_names:
                # Read each sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Skip empty sheets
                if df.empty:
                    continue
                
                # Convert DataFrame to a structured text format
                sheet_content = self._dataframe_to_text(df, sheet_name)
                
                # Create Document object
                doc = Document(
                    page_content=sheet_content,
                    metadata={
                        "source": file_path,
                        "sheet_name": sheet_name,
                        "file_type": "excel",
                        "rows": len(df),
                        "columns": len(df.columns)
                    }
                )
                documents.append(doc)
                
        except Exception as e:
            raise ValueError(f"Error processing Excel file: {str(e)}")
            
        return documents

    def _dataframe_to_text(self, df: pd.DataFrame, sheet_name: str) -> str:
        """
        Convert DataFrame to structured text format for embedding.
        
        Args:
            df (pd.DataFrame): DataFrame to convert
            sheet_name (str): Name of the Excel sheet
            
        Returns:
            str: Structured text representation of the DataFrame
        """
        # Start with sheet information
        text_parts = [f"Sheet: {sheet_name}"]
        text_parts.append(f"Dimensions: {len(df)} rows × {len(df.columns)} columns")
        text_parts.append("")
        
        # Add column headers
        text_parts.append("Columns: " + ", ".join(df.columns.astype(str)))
        text_parts.append("")
        
        # Add summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            text_parts.append("Numeric Data Summary:")
            for col in numeric_cols:
                if not df[col].empty:
                    stats = df[col].describe()
                    text_parts.append(f"{col}: Mean={stats['mean']:.2f}, Min={stats['min']:.2f}, Max={stats['max']:.2f}")
            text_parts.append("")
        
        # Add sample data (first few rows)
        text_parts.append("Sample Data:")
        sample_size = min(10, len(df))  # Show up to 10 rows
        for idx, row in df.head(sample_size).iterrows():
            row_text = []
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    value = "N/A"
                else:
                    value = str(value)
                row_text.append(f"{col}: {value}")
            text_parts.append(f"Row {idx + 1}: " + " | ".join(row_text))
        
        # If there are more rows, mention it
        if len(df) > sample_size:
            text_parts.append(f"... and {len(df) - sample_size} more rows")
        
        # Add unique values for categorical columns (if reasonable number)
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            unique_values = df[col].dropna().unique()
            if len(unique_values) <= 20:  # Only show if reasonable number of unique values
                text_parts.append(f"Unique values in {col}: {', '.join(map(str, unique_values))}")
        
        return "\n".join(text_parts)

    def create_embeddings(self, file_path: str):
        """
        Processes the file (PDF, PowerPoint, or Excel), creates embeddings, and stores them in Qdrant.

        Args:
            file_path (str): The file path to the document.

        Returns:
            str: Success message upon completion.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")

        # Determine file type and load accordingly
        file_extension = file_path.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            # Load PDF using existing method
            loader = UnstructuredPDFLoader(file_path)
            docs = loader.load()
        elif file_extension in ['ppt', 'pptx']:
            # Load PowerPoint using MarkItDown
            result = self.markitdown.convert(file_path)
            # Create Document object from MarkItDown result
            docs = [Document(page_content=result.text_content, metadata={"source": file_path, "file_type": "powerpoint"})]
        elif file_extension in ['xls', 'xlsx', 'xlsm', 'xlsb']:
            # Load Excel files
            docs = self._process_excel_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}. Supported formats: PDF, PowerPoint (ppt, pptx), Excel (xls, xlsx, xlsm, xlsb)")

        if not docs:
            raise ValueError(f"No documents were loaded from the {file_extension.upper()} file.")

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=250
        )
        splits = text_splitter.split_documents(docs)
        if not splits:
            raise ValueError("No text chunks were created from the documents.")

        # Create and store embeddings in Qdrant
        try:
            qdrant = Qdrant.from_documents(
                splits,
                self.embeddings,
                url=self.qdrant_url,
                prefer_grpc=False,
                collection_name=self.collection_name,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Qdrant: {e}")

        file_type = "Excel" if file_extension in ['xls', 'xlsx', 'xlsm', 'xlsb'] else file_extension.upper()
        return f"✅ {file_type} Vector DB Successfully Created and Stored in Qdrant!"
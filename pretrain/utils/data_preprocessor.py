## data_preprocessor.py
try:
    import torch
    import os
    import pickle
    # from torch_geometric.data import Data
    from EsperantoDataset import EsperantoDataset
    from utils.argument import TokenizerArguments
except ImportError as e:
    print(f"ImportError: {e}")
    raise e

from typing import Optional

class GraphCollection:
    def __init__(self):
        self.graphs = []

    def add_graph(self, graph):
        self.graphs.append(graph)

    def __getitem__(self, idx):
        return self.graphs[idx]

class GraphData:
    """
    A simple data structure to hold graph data.
    """
    def __init__(self,dataset,split_dict,batch):
        self.dataset = dataset
        self.split_dict = split_dict
    
    def __len__(self):
        return len(self.dataset)
    
    def __getitem__(self,index):
        return self.dataset[index]
    
class ProcessedGraphData:
    """
    A data structure for holding processed graph data.
    """
    def __init__(self, edge_index: torch.Tensor, node_features: torch.Tensor):
        self.edge_index = edge_index
        self.node_features = node_features

class DataPreprocessor:
    """
    The DataPreprocessor class is responsible for loading and preprocessing graph data.
    """
    def __init__(self, filepath: str, sequence = 128,batch = 32, tokenizaer_args: TokenizerArguments = None):
        # try:
        # dataset = np.load(filepath, allow_pickle=True)
        self.batch = batch
        dataset = []
        for filename in os.listdir(filepath):
            file_path = os.path.join(filepath, filename)
            with open(file_path, "rb") as f:
                graph = pickle.load(f)
            from torch_geometric.data import Data
            data = Data(x = graph['x'],edge_attr=graph['edge_attr'],y = graph['y'],edge_index = torch.tensor(graph['edge_index'],dtype=torch.long))
            dataset.append(data)

        self.dataset = dataset
        self.esperanto_dataset = EsperantoDataset(max_length = sequence, token_vocab_path = tokenizaer_args.token_vocab, token_merge_path = tokenizaer_args.token_merge)
        
       

    def process_data(self) -> Optional[GraphData]:
        """
        Loads graph data from a file.

        Parameters:
        - filepath (str): The path to the file containing the graph data.

        Returns:
        - GraphData: An instance of the GraphData class containing the loaded data, or None if an error occurs.
        """
        for i,data in enumerate(self.dataset):
            tensor_list = self.esperanto_dataset.tokenizer_node(data["x"])
            stacked_tensor = torch.stack(tensor_list)
            self.dataset[i]["x"] = stacked_tensor
            self.dataset[i]['edge_index'] = torch.tensor(data['edge_index'], dtype=torch.long).t()#可以保留
            tensor_list = self.esperanto_dataset.tokenizer_node(data["edge_attr"])
            stacked_tensor = torch.stack(tensor_list)
            self.dataset[i]["edge_attr"] = stacked_tensor
            if data['y']: 
                self.dataset[i]['Node labels'] = torch.tensor(data['y'], dtype=torch.float).repeat(10,1)
        return GraphData(self.dataset,self.split_dict,self.batch)

    def preprocess(self, graph_data: GraphData) -> Optional[ProcessedGraphData]:
        """
        Preprocesses the graph data.

        Parameters:
        - graph_data (GraphData): The graph data to preprocess.

        Returns:
        - ProcessedGraphData: An instance of the ProcessedGraphData class containing the processed data, or None if an error occurs.
        """
        if graph_data is None:
            print("Error: graph_data is None, cannot preprocess.")
            return None

        node_features_mean = graph_data.node_features.mean(dim=0, keepdim=True)
        node_features_std = graph_data.node_features.std(dim=0, keepdim=True) + 1e-6  # Adding a small value to avoid division by zero
        processed_node_features = (graph_data.node_features - node_features_mean) / node_features_std

        return ProcessedGraphData(edge_index=graph_data.edge_index, node_features=processed_node_features)

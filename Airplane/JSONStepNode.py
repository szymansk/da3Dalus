from Airplane.ConstructionStepNode import ConstructionStepNode


class JSONStepNode(ConstructionStepNode):
    def __init__(self, json_file_path: str, **kwargs):
        """
        :param geometry: the geometry, that is created in this node
        :param successors: all following construction steps
        """
        import json
        from Airplane.GeneralJSONEncoderDecoder import GeneralJSONDecoder

        self.json_file_path = json_file_path
        self._to_be_injected = kwargs
        _json_file = open(self.json_file_path)
        creator: ConstructionStepNode = json.load(_json_file,
                                                  cls=GeneralJSONDecoder,
                                                  **self._to_be_injected)
        _json_file.close()
        if "successors" in kwargs.keys():
            kwargs.pop("successors")
        if "creator" in kwargs.keys():
            kwargs.pop("creator")
        super().__init__(creator=creator.creator, successors=creator.successors, **kwargs)
        pass

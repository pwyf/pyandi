from ..standard import get_schema
from ..utils.abstract import GenericSet
from ..utils.querybuilder import QueryBuilder

from lxml import etree


class ActivitySet(GenericSet):
    def __init__(self, datasets, **kwargs):
        super().__init__()
        self._wheres = kwargs
        self._key = 'iati_identifier'
        self._filters = [
            'iati_identifier', 'title', 'description',
            'location', 'sector', 'planned_start',
            'actual_start', 'planned_end', 'actual_end',
        ]
        self.datasets = datasets
        self._filetype = 'activity'
        self._element = 'iati-activity'
        self._instance_class = Activity

    def __len__(self):
        total = 0
        for dataset in self.datasets:
            if dataset.filetype != self._filetype:
                continue
            if not dataset.is_valid():
                continue
            try:
                schema = get_schema(dataset.filetype, dataset.version)
            except:
                continue
            prefix = '//' + self._element
            query = QueryBuilder(
                schema,
                prefix=prefix,
                count=True
            ).where(**self._wheres)
            total += int(dataset.xml.xpath(query))
        return total

    def __iter__(self):
        for dataset in self.datasets:
            if dataset.filetype != self._filetype:
                continue
            if not dataset.is_valid():
                continue
            try:
                schema = get_schema(dataset.filetype, dataset.version)
            except:
                continue
            prefix = '//' + self._element
            query = QueryBuilder(
                schema,
                prefix=prefix,
            ).where(**self._wheres)
            activities_xml = dataset.xml.xpath(query)
            for xml in activities_xml:
                yield self._instance_class(xml, dataset, schema)


class Activity:
    def __init__(self, xml, dataset, schema):
        self.version = dataset.version
        self.xml = xml
        self.dataset = dataset
        self.schema = schema

    def __repr__(self):
        id_ = self.iati_identifier
        id_ = id_.strip() if id_ else '[No identifier]'
        return '<{} ({})>'.format(self.__class__.__name__, id_)

    @property
    def raw_xml(self):
        return etree.tostring(self.xml)

    @property
    def iati_identifier(self):
        id_ = self.schema.iati_identifier().exec(self.xml)
        if len(id_) > 0:
            return id_[0]
        return None

    @property
    def title(self):
        return self.schema.title().exec(self.xml)

    @property
    def description(self):
        return self.schema.description().exec(self.xml)

    @property
    def location(self):
        return self.schema.location().exec(self.xml)

    @property
    def sector(self):
        return self.schema.sector().exec(self.xml)

    @property
    def planned_start(self):
        date = self.schema.planned_start().exec(self.xml)
        return date[0] if len(date) > 0 else None

    @property
    def actual_start(self):
        date = self.schema.actual_start().exec(self.xml)
        return date[0] if len(date) > 0 else None

    @property
    def planned_end(self):
        date = self.schema.planned_end().exec(self.xml)
        return date[0] if len(date) > 0 else None

    @property
    def actual_end(self):
        date = self.schema.actual_end().exec(self.xml)
        return date[0] if len(date) > 0 else None

    @property
    def start(self):
        start = self.actual_start
        if start:
            return start
        return self.planned_start

    @property
    def end(self):
        end = self.actual_end
        if end:
            return end
        return self.planned_end

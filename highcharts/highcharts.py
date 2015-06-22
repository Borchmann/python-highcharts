#!/usr/bin/python

"""
Python-Highcharts is a Python wrapper for Highcharts graph library.
For Highcharts Licencing Visit:
http://shop.highsoft.com/highcharts.html
Project location : xxxxx
"""

from __future__ import unicode_literals
from optparse import OptionParser
from jinja2 import Environment, PackageLoader
# from slugify import slugify
import json, uuid
import datetime, random, os, inspect
from _abcoll import Iterable
from options import BaseOptions, ChartOptions, \
    ColorsOptions, CreditsOptions, DrilldownOptions, ExportingOptions, \
    GlobalOptions, LabelsOptions, LangOptions, \
    LegendOptions, LoadingOptions, NavigationOptions, PaneOptions, \
    PlotOptions, SeriesData, SubtitleOptions, TitleOptions, \
    TooltipOptions, xAxisOptions, yAxisOptions

from highchart_types import Series, SeriesOptions, HighchartsError, MultiAxis
from common import Formatter, CSSObject, JSfunction, RawJavaScriptText, CommonObject, ArrayObject

CONTENT_FILENAME = "./content.html"
PAGE_FILENAME = "./page.html"

pl = PackageLoader('highcharts', 'templates')
jinja2_env = Environment(lstrip_blocks=True, trim_blocks=True, loader=pl)

template_content = jinja2_env.get_template(CONTENT_FILENAME)
template_page = jinja2_env.get_template(PAGE_FILENAME)
    
DEFAULT_POINT_INTERVAL = 86400000

FORMAT_SPECIAL_CASES = {
    "formatter": "formatter",
    "labelFormatter": "formatter",
    "pointStart": "skip_quotes",
    "events": "skip_quotes",
    "load": "skip_quotes",
    "multiaxis": "multiaxis"
}

def stab(tab=1):
    """
    create space tabulation
    """
    return ' ' * 4 * tab


class Highcharts(object):
    """
    Highcharts Base class.
    """
    #: chart count
    count = 0
    #:  directory holding the assets (bower_components)
    assets_directory = './bower_components/'

    # this attribute is overriden by children of this
    # class
    CHART_FILENAME = None
    template_environment = Environment(lstrip_blocks=True, trim_blocks=True,
                                       loader=pl)

    def __init__(self, **kwargs):
        """
        This is the base class for all the charts. The following keywords are
        accepted:
        :keyword: **display_container** - default: ``True``
        """
        # set the model
        self.model = self.__class__.__name__  #: The chart model,
        self.div_name = kwargs.get("renderTo", "container")

        # an Instance of Jinja2 template
        self.template_page_highcharts = template_page
        self.template_content_highcharts = template_content
        
        # set Javascript src

        self.JSsource = [
                'https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js',
                'https://code.highcharts.com/highcharts.js',
                'https://code.highcharts.com/highcharts-more.js',
                'https://code.highcharts.com/modules/exporting.js'
            ]

        # set CSS src

        self.CSSsource = [
                'https://www.highcharts.com/highslide/highslide.css',
            ]

        # set data
        self.data = []
        self.data_temp = []
        
        # accepted keywords

        self.div_style = kwargs.get('style', '')
        self.drilldown_flag = kwargs.get('drilldown_flag', False)
        self.date_flag = kwargs.get('date_flag', False)

        # None keywords attribute that should be modified by methods
        # We should change all these to _attr

        self.htmlcontent = ''  #: written by buildhtml
        self.htmlheader = ''
        #: Place holder for the graph (the HTML div)
        #: Written by ``buildcontainer``
        self.container = u''
        #: Header for javascript code
        self.containerheader = u''
        
        #: Javascript code as string
        self.jschart = None
        # self.custom_tooltip_flag = False
        # self.tooltip_condition_string = ''
        # self.charttooltip = ''
        self.serie_no = 1

        # Default Nulls // ?
        self.hold_point_start = None
        self.hold_point_interval = None
        self.start_date_set = None

        # Bind Base Classes to self
        self.options = {
            "chart": ChartOptions(),
            "colors": ColorsOptions(),
            "credits": CreditsOptions(),
            #"data": #NotImplemented
            "drilldown": DrilldownOptions(),
            "exporting": ExportingOptions(),
            "labels": LabelsOptions(),
            "legend": LegendOptions(),
            "loading": LoadingOptions(),
            "navigation": NavigationOptions(),
            "pane": PaneOptions(),
            "plotOptions": PlotOptions(),
            "series": SeriesData(),
            "subtitle": SubtitleOptions(),
            "title": TitleOptions(),
            "tooltip": TooltipOptions(),
            "xAxis": xAxisOptions(),
            "yAxis": yAxisOptions(),
        }

        self.setOptions = {
            "global": GlobalOptions(),
            "lang": LangOptions(),
        }

        self.__load_defaults__()

        # Process kwargs
        allowed_kwargs = [
            "width",
            "height",
            "renderTo",
            "backgroundColor",
            "events",
            "marginBottom",
            "marginTop",
            "marginRight",
            "marginLeft"
        ]

        for keyword in allowed_kwargs:
            if keyword in kwargs:
                self.options['chart'].update_dict(**{keyword:kwargs[keyword]})
        # Some Extra Vals to store:
        self.data_set_count = 0


    def __load_defaults__(self):
        self.options["chart"].update_dict(renderTo='container')
        self.options["title"].update_dict(text='A New Highchart')
        self.options["credits"].update_dict(enabled=False)


    def title(self, title=None):
        """ Bind Title """
        if not title:
            return self.options["title"].text
        else:
            self.options["title"].update_dict(text=title)


    def colors(self, colors=None):
        """ Bind Color Array """
        if not colors:
            return self.options["colors"].__dict__.values() if self.options['colors'] is not None else []
        else:
            self.options["colors"].set_colors(colors)


    def chart_background(self, background=None):
        """ Apply Chart Background """
        if not background:
            return self.options["chart"].backgroundColor
        else:
            self.options["chart"].update_dict(backgroundColor=background)

    def set_JSsource(self, new_src):
        if isinstance(new_src, list):
            for h in list:
                self.JSsource.append(h)
        else:
            self.JSsource.append(new_src)

    def set_CSSsource(self, new_src):
        if isinstance(new_src, list):
            for h in new_src:
                self.CSSsource.append(h)
        else:
            self.CSSsource.append(new_src)


    def set_x_axis(self, **kwargs):
        self.options["xAxis"].update_dict(**kwargs)


    def set_y_axis(self, **kwargs):
        self.options["yAxis"].update_dict(**kwargs)


    def set_start_date(self, date):
        """ Set Plot Start Date """
        if isinstance(date, (int, float)):
            date = datetime.datetime.fromtimestamp(date)
        elif not isinstance(date, datetime.datetime):
            error = "Start Date Format Currently Not Supported: %s" % date
            raise HighchartError(error)
        date_dict = {
            "year": date.year,
            "month": date.month - 1,
            "day": date.day,
            "hour": date.hour,
            "minute": date.minute,
            "second": date.second,
        }
        formatted_date = "Date.UTC({year}, {month}, {day}, {hour}, {minute}, {second})"
        formatted_date = formatted_date.format(**date_dict)
        if not self.options['plotOptions'].__dict__:
            self.hold_point_start = formatted_date
            self.hold_point_interval = DEFAULT_POINT_INTERVAL
        hold_iterable = self.options['plotOptions'].__dict__.items()
        for series_type, series_options in hold_iterable:
            series_options.process_kwargs({'pointStart':formatted_date},
                series_type=series_type)
            if not 'pointInterval' in series_options.__dict__:
                series_options.process_kwargs({
                    'pointInterval':DEFAULT_POINT_INTERVAL},
                    series_type=series_type,
                    supress_errors=True)
        self.options['tooltip'].update_dict(formatter=Formatter('date'))
        self.options['xAxis'].update_dict(type='datetime')
        self.start_date_set = True


    def set_interval(self, interval):
        """ Set Plot Step Interval """
        if not isinstance(interval, int):
            raise HighchartError("Interval Value Must Be An Integer")
        # Unset Any Held Values To Avoid Them Overwriting This Value
        if self.hold_point_interval:
            self.hold_point_interval = None
        if not self.options['plotOptions'].__dict__:
            self.hold_point_interval = interval
        for hold_item in self.options['plotOptions'].__dict__.items():
            series_type, series_options = hold_item
            series_options.process_kwargs({'pointInterval':interval},
                series_type=series_type)
        if not self.start_date_set:
            print "Set The Start Date With .set_start_date(date)"


    def add_data_set(self, data, series_type="line", name=None, **kwargs):
        """ Update Plot Options With Defaults If None Exist """
        self.data_set_count += 1
        if not name:
            name = "Series %d" % self.data_set_count
        kwargs.update({'name':name})
        if self.hold_point_start:
            kwargs.update({"pointStart":self.hold_point_start})
            self.hold_point_start = None
        if self.hold_point_interval:
            kwargs.update({"pointInterval":self.hold_point_interval})
            self.hold_point_interval = None
        if series_type not in self.options["plotOptions"].__dict__:
            to_update = {series_type:SeriesOptions(series_type=series_type,
                supress_errors=True, **kwargs)}
            self.options["plotOptions"].update_dict(**to_update)
        series_data = Series(data, series_type=series_type, \
            supress_errors=True, **kwargs)
        self.data_temp.append(series_data)
        #self.options["series"].data.append(series_data)


    def set_options2(self, options, force_options=False):
        """ Set Plot Options """
        if force_options:
            for k, v in options.items():
                self.options.update({k:v})
        else:
            new_options = {}
            for key, option_data in options.items():
                data = {}
                for key2, val in option_data.items():
                    if isinstance(val, dict):
                        for key3, val2 in val.items():
                            data.update({key2+"_"+key3:val2})
                    else:
                        data.update({key2:val})
                new_options.update({key:data})
            for key, val in new_options.items():
                self.options[key].update_dict(**val)


    def set_options(self, option_type, option_dict, force_options=False):
        """ Set Plot Options """
        if force_options:
            self.options[option_type].update(option_dict)
        else:
            self.options[option_type].update_dict(**option_dict)


    def set_containerheader(self, containerheader):
        """Set containerheader"""
        self.containerheader = containerheader


    def __str__(self):
        """return htmlcontent"""
        self.buildhtml()
        return self.htmlcontent


    def buildcontent(self):
        """Build HTML content only, no header or body tags. To be useful this
        will usually require the attribute `juqery_on_ready` to be set which
        will wrap the js in $(function(){<regular_js>};)
        """
        self.buildcontainer()
        # if the subclass has a method buildjs this method will be
        # called instead of the method defined here
        # when this subclass method is entered it does call
        # the method buildjschart defined here
        self.buildjschart()
        #self.option = json.dumps(self.__export_options__())
        self.option = json.dumps(self.options, cls = HighchartsEncoder)
        self.setoption = json.dumps(self.setOptions, cls = HighchartsEncoder)

        #self.data = json.dumps(data_formatter(self.options['series']))
        self.data = json.dumps(self.data_temp, cls = HighchartsEncoder)
        self.htmlcontent = self.template_content_highcharts.render(chart=self)


    def buildhtml(self):
        """Build the HTML page
        Create the htmlheader with css / js
        Create html page
        Add Js code for highcharts
        """
        self.buildcontent()
        self.buildhtmlheader()
        self.content = self.htmlcontent
        self.htmlcontent = self.template_page_highcharts.render(chart=self)


    def buildhtmlheader(self):
        """generate HTML header content"""
        #Highcharts lib/ needs to make sure it's up to date
        
        self.header_css = [
            '<link href="%s" rel="stylesheet" />' % h for h in self.CSSsource
        ]

        self.header_js = [
            '<script type="text/javascript" src="%s"></script>' % h for h in self.JSsource
        ]

        self.htmlheader = ''
        for css in self.header_css:
            self.htmlheader += css
        for js in self.header_js:
            self.htmlheader += js


    def buildcontainer(self):
        """generate HTML div"""
        if self.container:
            return

        # Create HTML div with style
        if self.options['chart'].width:
            if str(self.options['chart'].width)[-1] != '%':
                self.div_style += 'width:%spx;' % self.options['chart'].width
            else:
                self.div_style += 'width:%s;' % self.options['chart'].width
        if self.options['chart'].height:
            if str(self.options['chart'].height)[-1] != '%':
                self.div_style += 'height:%spx;' % self.options['chart'].height
            else:
                self.div_style += 'height:%s;' % self.options['chart'].height
        # if self.div_style:
        #     self.div_style = 'style="%s"' % self.div_style

        self.container = self.containerheader + \
            '<div id="%s" style="%s"></div>\n' % (self.div_name, self.div_style)


    def buildjschart(self):
        """generate javascript code for the chart"""
        self.jschart = ''

        # add custom tooltip string in jschart
        # default condition (if build_custom_tooltip is not called explicitly with date_flag=True)

        # if self.tooltip_condition_string == '':
        #     self.tooltip_condition_string = 'var y = String(graph.point.y);\n'

        # Include data
        # self.series_js = json.dumps(self.series)


class TemplateMixin(object):
    """
    A mixin that override buildcontent. Instead of building the complex
    content template we exploit Jinja2 inheritance. Thus each chart class
    renders it's own chart template which inherits from content.html
    """
    def buildcontent(self):
        """Build HTML content only, no header or body tags. To be useful this
        will usually require the attribute `juqery_on_ready` to be set which
        will wrap the js in $(function(){<regular_js>};)
        """
        self.buildcontainer()
        # if the subclass has a method buildjs this method will be
        # called instead of the method defined here
        # when this subclass method is entered it does call
        # the method buildjschart defined here
        self.buildjschart()
        self.htmlcontent = self.template_chart_highcharts.render(chart=self)


def set_temp_dir(temp_dir):
    globals()['TMP_DIR'] = temp_dir

class HighchartError(Exception):
    """ Highcharts Error Class """
    def __init__(self, *args):
        Exception.__init__(self, *args)
        self.args = args


class HighchartsEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        json.JSONEncoder.__init__(self, *args, **kwargs)
        self._replacement_map = {}

    def default(self, obj):
        if isinstance(obj, RawJavaScriptText):
            key = uuid.uuid4().hex
            self._replacement_map[key] = obj.get_jstext()
            return key
        elif isinstance(obj, datetime.datetime):
            utc = obj.utctimetuple()
            obj = (u"Date.UTC({year},{month},{day},{hours},{minutes},{seconds},{millisec})"
                    .format(year=utc[0], month=utc[1]-1, day=utc[2], hours=utc[3],
                            minutes=utc[4], seconds=utc[5], millisec=obj.microsecond/1000))
            return RawJavaScriptText(obj)
        elif isinstance(obj, BaseOptions):
            return obj.__jsonable__()
        elif isinstance(obj, CSSObject) or isinstance(obj, Formatter) or isinstance(obj, JSfunction):
            return obj.__options__()
        elif isinstance(obj, SeriesOptions) or isinstance(obj, Series) or isinstance(obj, MultiAxis):
            return obj.__options__()
        elif isinstance(obj, CommonObject) or isinstance(obj, ArrayObject):
            return obj.__options__()
        else:
            return json.JSONEncoder.default(self, obj)

    def encode(self, obj):
        result = json.JSONEncoder.encode(self, obj)
        for k, v in self._replacement_map.items():
             result = result.replace('"%s"' % (k,), v)
        return result

def _main():
    """
    Parse options and process commands
    """
    # Parse arguments
    usage = "usage: highcharts.py [options]"
    parser = OptionParser(usage=usage, version="python-highcharts - Charts generator with Highcharts library")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print messages to stdout")

    (options, args) = parser.parse_args()


if __name__ == '__main__':
    _main()
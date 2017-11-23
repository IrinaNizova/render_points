# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from zipfile import ZipFile, BadZipfile
import mapnik
import os, subprocess

from mymap.settings import *

from django.shortcuts import render


def create_rule(expression, color):
    rule = mapnik.Rule()
    rule.filter = mapnik.Expression(expression)
    point_symbolizer = mapnik.MarkersSymbolizer()
    point_symbolizer.fill = mapnik.Color(*color)
    rule.symbols.append(point_symbolizer)
    return rule


def create_map():
    map = mapnik.Map(800, 600)
    map.background = mapnik.Color('rgb(0,0,0,0)')

    style = mapnik.Style()
    rule_orange = create_rule('([productivi] > 30) and ([productivi] < 70)', (250,100,0))
    rule_green = create_rule('[productivi] >= 70', (0,250,0))
    rule_red = create_rule('[productivi] <= 30', (250,0,0))

    style.rules.extend([rule_green, rule_red, rule_orange])
    map.append_style('tracking_points', style)

    layer = mapnik.Layer('tracking_points')
    db_settings = DATABASES['default']
    layer.datasource = mapnik.PostGIS(host=db_settings['HOST'],port=db_settings['PORT'],
                                      user=db_settings['USER'],password=db_settings['PASSWORD'],
                                      dbname=db_settings['NAME'],table='paints')
    layer.styles.append('tracking_points')
    map.layers.append(layer)
    map.zoom_all()
    return map

def dump_sql(filepath):

    os.environ['PATH'] += r';C:\Program Files\PostgreSQL\10\bin'
    os.environ['PGHOST'] = DATABASES['default']['HOST']
    os.environ['PGPORT'] = DATABASES['default']['PORT']
    os.environ['PGUSER'] = DATABASES['default']['USER']
    os.environ['PGPASSWORD'] = DATABASES['default']['PASSWORD']
    os.environ['PGDATABASE'] = DATABASES['default']['NAME']

    full_dir = os.walk(filepath)
    shapefile_list = []
    for source, dirs, files in full_dir:
        for file_ in files:
            if file_[-3:] == 'shp':
                shapefile_path = os.path.join(filepath, file_)
                shapefile_list.append(shapefile_path)

    for shape_path in shapefile_list:
        cmds = 'shp2pgsql "' + shape_path + '" paints | psql '
        return subprocess.call(cmds, shell=True)


def load_map(request):
    errors = []
    if 'filename' in request.GET:
        filename = request.GET['filename']

        if os.path.isfile(filename):
            try:
                z = ZipFile(filename)
                z.extractall(path=os.path.dirname(filename))
                dump_error = dump_sql(os.path.dirname(filename))
                if dump_error:
                    errors.append('Can not create postgis table from files')
                mapnik.render_to_file(create_map(), 'static/fromarchive/tracking_points.png', 'png')
            except BadZipfile:
                errors.append('File is not a zip file')

        else:
            errors.append('Can not find file on path %s' % filename)

    return render(request, 'map.html', {'errors': errors})




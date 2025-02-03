import ee
import matplotlib.pyplot as plt
import rasterio
import requests
import os

from requests import Response
from io import BytesIO

class SentinelRGBFromEE:
    def __init__(self):
        self.collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')

    def process_collection(self, *, aoi: ee.Geometry, date_range: list[str], custom_filters: dict[str, dict]):
        collection = self.collection.filterBounds(aoi)
        collection = collection.filterDate(date_range[0], date_range[1])

        if custom_filters is not None:
            for key in custom_filters:
                property = key
                filter = custom_filters[key]['filter']
                value = custom_filters[key]['value']

                collection = collection.filter(filter(property, value))

        self.collection = collection

    def get_first_image(self, *, aoi: ee.Geometry):
        tci_bands = ['TCI_R', 'TCI_G', 'TCI_B']
        image = self.collection.first().select(tci_bands)

        if aoi:
            image = image.clip(aoi)

        return image

    def request_image(self, image: ee.Image, *, url_params: dict[str, any]):
        url = image.getDownloadUrl(url_params)
        response = requests.get(url)

        return response

    def plot_image(self, *, response: Response, img_id: str, method: str = 'multiband'):
        if method == 'multiband':
            with rasterio.MemoryFile(BytesIO(response.content)) as memfile:
                with memfile.open() as src:
                    img = src.read([1, 2, 3])
                    img = img.transpose(1, 2, 0)

                    plt.imshow(img)
                    plt.title(img_id, fontsize=8)
                    plt.axis('off')
                    plt.tight_layout()
                    plt.show()
                    
                    while plt.get_fignums():
                        QApplication.processEvents()

    def write_image(self, *, response: Response, output_path: str):
        with rasterio.MemoryFile(BytesIO(response.content)) as memfile:
            with memfile.open() as src:
                profile = src.profile
                img = src.read()

                with rasterio.open(output_path, 'w', **profile) as dst:
                    dst.write(img)

class CustomFilters():
    def __init__(self):
        self.filters = {}

    def add_filter(self, *, property: str, filter: ee.Filter, value: any):
        self.filters[property] = {
            'filter': filter,
            'value': value,
        }

class BoolMessageBox(QMessageBox):
    def __init__(self, message):
        super().__init__()
        self.setIcon(QMessageBox.Question)
        self.setText(message)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

def main(*, project: str, output_folder: str):
    # Autenticação e inicialização do Earth Engine
    ee.Authenticate()
    ee.Initialize(project=cloud_project)

    # Area de interesse
    x_max = -46.9571818723517254
    y_max = -14.8772245884183416
    x_min = -46.7816836599576504
    y_min = -14.6975095089156795
    aoi = ee.Geometry.Rectangle(coords=[[x_max,y_max],[x_min,y_min]])

    # Preparação da coleção de imagens
    date_rng = ['2025-01-01', '2025-01-30']

    custom_filters = CustomFilters()
    custom_filters.add_filter(property='CLOUDY_PIXEL_PERCENTAGE',
                              filter=ee.Filter.lte,
                              value=30)

    s2 = SentinelRGBFromEE()
    s2.process_collection(aoi=aoi,
                          date_range=date_rng,
                          custom_filters=custom_filters.filters)

    # Seleção da primeira imagem na coleção
    img = s2.get_first_image(aoi=aoi)

    img_id = img.get('PRODUCT_ID').getInfo()

    # Requisição da imagem
    params = {'region': aoi,
                  'scale': 10,
                  'format': 'GEO_TIFF'}

    res = s2.request_image(img, url_params=params)

    # Plotagem
    plot = BoolMessageBox('Deseja visualizar a imagem?')

    plot_res = plot.exec_()

    if plot_res == QMessageBox.Yes:
        s2.plot_image(img_id=img_id, response=res)

    # Gravação em disco
    file_name = f'{img_id}.tiff'
    file_path = os.makedirs(f'{output_dir}{file_name}')

    write = BoolMessageBox('Deseja gravar a imagem em disco?')

    write_res = write.exec_()

    if write_res == QMessageBox.Yes:
        s2.write_image(response=res, output_path=file_path)

    # Abrir o arquivo no QGIS
    if(os.path.isfile(output)):
        raster = QgsRasterLayer(file_path, img_id)
        QgsProject.instance().addMapLayer(raster)

if __name__ == '__main__':
    cloud_project = ''
    output_dir = ''

    main(project=cloud_project, output_folder=output_dir)
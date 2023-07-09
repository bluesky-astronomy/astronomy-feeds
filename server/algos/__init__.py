from .astro import algorithm as astro_algorithm
from .astro_all import algorithm as astro_all_algorithm

algos = {
    astro_algorithm.uri: astro_algorithm.handler,
    astro_all_algorithm.uri: astro_all_algorithm.handler,
}

"""
Скрипт для автоматического удаления устаревших видеозаписей.
При запуске проверяет свободное место на диске и, если его мало,
запускает удаление самых старых записей.

Предназначен для периодического запуска cron'ом.
"""

# ПАПКА С ВИДЕОЗАПИСЯМИ С РАЗНЫХ КАМЕР
WORKDIR = "/home/rodion/VIDEOREPO/"
# МИНИМАЛЬНЫЙ ПРОЦЕНТ СВОБОДНОЙ ПАМЯТИ
# (если свободной памяти меньше, то будет начинаться очистка)
FREE_MEM_CRITICAL_PERCENT = 0.15
# ОЖИДАЕМЫЙ ПРОЦЕНТ СВОБОДНОЙ ПАМЯТИ ПОСЛЕ ОЧИСТКИ
# (скрипт будет удалять файлы пока не достигнет
# этого процента или файлы не кончатся)
FREE_MEM_AFTER_CLEAR_PERCENT = 0.20
# ПУТЬ К ЛОГ-ФАЙЛУ
# (туда будут писаться сообщения от скрипта)
PATH2LOG = "/home/rodion/VIDEOREPO/video_autoremove.log"

import logging                  # nopep8
import os                       # nopep8
import re                       # nopep8
import shutil                   # nopep8
from pathlib import Path        # nopep8
from typing import Union        # nopep8


def recursive_get_subdirs(target: Union[str, os.PathLike]) -> list[Path]:
    """Получает все дочерние директории для выбранной директории"""
    subdirs = (Path(root).absolute() for root, _, _ in os.walk(Path(target)))
    subdirs = list(set(subdirs))
    return subdirs


def find_all_video_folders(
        target: Union[str, os.PathLike],
        regex_pattern: str,
) -> list[Path]:
    """Выбирает все папки, по определённому паттерну"""
    target = Path(target).absolute()
    dirs = recursive_get_subdirs(target)
    regex = re.compile(regex_pattern)
    dirs = [d for d in dirs if regex.findall(str(d))]
    return dirs


def get_free_memory_percent(workdir: Union[str, os.PathLike]) -> float:
    """
    Возвращает занятость памяти в диапазоне [0.0; 1.0].

    Здесь 1.0 - 100% памяти свободно, 0.0 - вся память занята.
    """
    total, used, free = shutil.disk_usage(workdir)
    return free / total


def remove_record_directory(
        path: Union[str, os.PathLike],
        autoremove_empty_parent: bool = True,
) -> None:
    """
    Удаляет директорию и всё её содержимое.
    Если второй аргумент установлен в True, то удаляет
    родительскую папку, если она оказывается пуста.
    """
    folder = Path(path)
    shutil.rmtree(folder)
    logger.info(f"Удалена папка с записями: {folder}")
    if autoremove_empty_parent and len(os.listdir(folder.parent)) == 0:
        shutil.rmtree(folder.parent)
        logger.info(f"Удалена пустая родительская папка: {folder.parent}")


def main():
    logger.info("Скрипт запущен")
    workdir = Path(WORKDIR).absolute()
    logger.info(f"Рабочая директория: {workdir}")

    if not os.path.exists(workdir) or not workdir.is_dir():
        logger.error("Директория не найдена! Завершение")
        return

    video_folder_regex = r".*\d+/\d{4}-\d{2}-\d{2}/\d+$"
    videos = find_all_video_folders(WORKDIR, video_folder_regex)
    videos.sort(
        reverse=True,
        key=lambda d: int(re.findall(r"/(\d+)$", str(d))[0])
    )
    logger.info(f"Найдено {len(videos)} папок с записями")
    logger.info(f"Свободно {100 * get_free_memory_percent(workdir):.1f}% памяти")
    logger.info(f"Пороговые значения для свободной памяти: "
                f"{100 * FREE_MEM_CRITICAL_PERCENT:.1f}% "
                f"{100 * FREE_MEM_AFTER_CLEAR_PERCENT:.1f}% ")

    if get_free_memory_percent(workdir) < FREE_MEM_CRITICAL_PERCENT:
        logger.info("Очистка начата")
        while len(videos) > 0 and get_free_memory_percent(workdir) < FREE_MEM_AFTER_CLEAR_PERCENT:
            # свободной памяти меньше определённого процента
            # удаляем по 1 папке, пока не станет лучше или папки не кончатся
            video_folder = videos.pop()
            remove_record_directory(video_folder)

        if get_free_memory_percent(workdir) < FREE_MEM_AFTER_CLEAR_PERCENT:
            logger.warning("Очистка завершена, однако не было освобождено "
                           "достаточно памяти - она потенциально занята чем-то другим")

        logger.info("Очистка закончена")

    logger.info(f"Свободно {100 * get_free_memory_percent(workdir):.1f}% памяти")
    logger.info("Скрипт завершен")


if __name__ == '__main__':
    _formatter = logging.Formatter('%(asctime)s  %(levelname)s: %(message)s')
    _file_handler = logging.FileHandler(PATH2LOG)
    _file_handler.setLevel(logging.INFO)
    _file_handler.setFormatter(_formatter)
    _console_handler = logging.StreamHandler()
    _console_handler.setLevel(logging.INFO)
    _console_handler.setFormatter(_formatter)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(_file_handler)
    logger.addHandler(_console_handler)

    try:
        main()
    except Exception as e:
        logger.exception("Произошлая ошибка: ", exc_info=e)

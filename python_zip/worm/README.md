Running the worm code
==================================================

1. Make it into a bin file, by running ./make_python_zip_executable.sh worm
2. Make a POST request, by running 
    curl -X POST 'http://{hostname}:{port}/worm_entrance?args=-gp&args={port}&args=-ts&args={target_size}&args=-p&args={random_worm_port}'     --data-binary @../python_zip_example/worm.bin


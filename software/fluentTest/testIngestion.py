import unittest
import requests


class TestPost(unittest.TestCase):
  
    
    def test_get(self):
        resp = requests.get('http://10.0.46.242:4443')
        self.assertEqual(resp.status_code, 200)
        print (resp.status_code)
    
    
    def test_post(self):
        var_name_request = 'var1'
        value_request = "dummydummydummy123"
        req = requests.post('http://10.0.46.242:4443',data={var_name_request: value_request})
        var_name_response = req.text.split('=')[0]
        value_response = req.text.split('=')[1]
        self.assertEqual(var_name_request, var_name_response)
        self.assertEqual(value_request, value_response)
        

if __name__ == "__main__":
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPost)
    unittest.TextTestRunner(verbosity=2).run(suite)
package org.slapos.slap;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Map;

import javax.ws.rs.core.MediaType;

import org.codehaus.jackson.JsonGenerationException;
import org.codehaus.jackson.jaxrs.JacksonJsonProvider;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;

import com.sun.jersey.api.client.Client;
import com.sun.jersey.api.client.ClientResponse;
import com.sun.jersey.api.client.WebResource;
import com.sun.jersey.api.client.config.ClientConfig;
import com.sun.jersey.api.client.config.DefaultClientConfig;

/**
 * Simple Jersey Client wrapper, including url of the slapos master.
 */
class ClientWrapper {
	private Client client;
	private final String masterUri;

	public ClientWrapper(String masterUri) {
		//TODO check uri validity (http and https)
		//TODO check presence of end /
		this.masterUri = masterUri;
		ClientConfig config = new DefaultClientConfig();
		config.getClasses().add(JacksonJsonProvider.class);
		client = Client.create(config);
	}

	/**
	 * Creates a WebResource with master url + given uri.
	 * @param uri
	 */
	public WebResource resource(String uri) {
		return client.resource(masterUri + uri);
	}

	public static String object2Json(Object parameterList, String type) {
		String parameterListJson = null;
		StringWriter sw = new StringWriter();
		//TODO correct encoding handling, maybe do not use Writer. see javadoc for JsonEncoding
		ObjectMapper mapper = new ObjectMapper();
		try {
			if (type.equalsIgnoreCase("ComputerPartition")) {
				mapper.writeValue(sw, (ComputerPartition) parameterList);
			} else {
				mapper.writeValue(sw, (Map<String, Object>) parameterList);
			}
			parameterListJson = sw.toString();
		} catch (JsonGenerationException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (JsonMappingException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return parameterListJson;
	}

	public String get(String uri) {
		WebResource webResource = resource(uri);
		String response = webResource.accept(MediaType.APPLICATION_JSON_TYPE).get(String.class);
		//TODO check that exception is thrown when !200
		return response;
	}

	/**
	 * Takes a Map<String, Object>, converts it to json, and send it to URI.
	 * @param uri
	 * @param parameterList
	 * @return
	 * @throws Exception
	 */
	public String post(String uri, Map<String, Object> parameterList) throws Exception {
		// Converts it to JSON
		// TODO better automatic marshalling with jackson.
		String parameterListJson = ClientWrapper.object2Json(parameterList, "map");
		return post(uri, parameterListJson);
	}

	/**
	 * Makes a POST request to the specified URI with the corresponding string as parameter to send
	 * @param uri
	 * @param JsonObject
	 * @return
	 * @throws Exception
	 */
	// TODO content type?
	public String post(String uri, String JsonObject) throws Exception {
		WebResource webResource = resource(uri);
		// FIXME there must exist a way to send a generic object as parameter and have it converted automatically to json.
		ClientResponse response = webResource.type(MediaType.APPLICATION_JSON_TYPE).accept(MediaType.APPLICATION_JSON_TYPE).post(ClientResponse.class, JsonObject); //new GenericType<List<StatusBean>>() {}
		//TODO automatic unmarshal
		if (response.getStatus() == 200) {
			return response.getEntity(String.class);
		}
		//TODO correct exception
		throw new Exception("Server responded with wrong code : " + response.getStatus() + " when requesting " + uri);
	}
}